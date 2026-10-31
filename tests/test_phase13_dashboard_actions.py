"""Phase 13 Regression & Feature Tests for Dashboard Actions, Active Queues & Recommendation Deduplication."""

import json
import urllib.request
import pytest
from datetime import datetime, timezone

from job_monitor.dashboard.server import DashboardServer
from job_monitor.db.storage import JobStorage
from job_monitor.ingestion.deduplicator import JobDeduplicator
from job_monitor.models.application import Application, ApplicationStatus, InterviewStage
from job_monitor.models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod
from job_monitor.reports.excel_exporter import ExcelExporter
from job_monitor.scoring.ranking import JobQueryService, ScoredJobRecord



@pytest.fixture
def temp_storage(tmp_path):
    """Fixture providing temporary SQLite storage."""
    db_file = str(tmp_path / "test_phase13_jobs.db")
    storage = JobStorage(db_path=db_file)
    return storage


@pytest.fixture
def target_java_job(temp_storage):
    """Fixture creating a top target Java backend engineer job."""
    job = NormalizedJob(
        id="job-target-java",
        source_name="remotive",
        external_id="ext-target-1",
        url="https://example.com/job/target-java",
        title="Senior Java Spring Boot Engineer",
        company_name="Camunda Systems",
        is_remote=True,
        location_requirement="Worldwide",
        employment_type=EmploymentType.FULL_TIME,
        salary_min=120000,
        salary_max=150000,
        salary_currency="USD",
        salary_period=SalaryPeriod.ANNUAL,
        annualized_min_usd=120000,
        annualized_max_usd=150000,
        original_salary_text="$120k - $150k",
        category="Software Development",
        tags=["java", "spring boot", "postgres", "microservices"],
        description_raw="<p>Looking for a Senior Java Spring Boot Developer. Worldwide remote.</p>",
        description_text="Looking for a Senior Java Spring Boot Developer. Worldwide remote.",
        content_hash="hash-target-java",
        canonical_fingerprint="fingerprint-target-java",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )
    temp_storage.save_normalized_job(job)
    return job


@pytest.fixture
def fast_cash_job(temp_storage):
    """Fixture creating a contract fast-cash job."""
    job = NormalizedJob(
        id="job-fast-cash",
        source_name="jobicy",
        external_id="ext-fast-cash",
        url="https://example.com/job/fast-cash",
        title="Java API Contract Engineer",
        company_name="FastPay Inc",
        is_remote=True,
        location_requirement="Worldwide",
        employment_type=EmploymentType.CONTRACT,
        salary_min=65,
        salary_max=85,
        salary_currency="USD",
        salary_period=SalaryPeriod.HOURLY,
        annualized_min_usd=130000,
        annualized_max_usd=170000,
        original_salary_text="$65 - $85 / hr",
        category="Software Engineering",
        tags=["java", "rest api", "contract"],
        description_raw="<p>Urgent 6-month contract for Java API engineer.</p>",
        description_text="Urgent 6-month contract for Java API engineer.",
        content_hash="hash-fast-cash",
        canonical_fingerprint="fingerprint-fast-cash",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )
    temp_storage.save_normalized_job(job)
    return job


class TestPhase13RegressionAndFeatures:

    def test_1_marking_job_as_applied_removes_from_active_recommendations(self, temp_storage, target_java_job):
        """1. Marking a job as Applied removes it from active recommendation results."""
        query_svc = JobQueryService(storage=temp_storage)

        # Before applying: Job is in Apply First
        apply_before = query_svc.get_apply_first_jobs()
        assert any(r.job.id == target_java_job.id for r in apply_before)

        # Mark as applied
        temp_storage.mark_as_applied(target_java_job.id)

        # After applying: Job must NOT be in Apply First or any active recommendation view
        apply_after = query_svc.get_apply_first_jobs()
        assert not any(r.job.id == target_java_job.id for r in apply_after)

        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_2_applied_job_remains_accessible_in_application_tracker(self, temp_storage, target_java_job):
        """2. An Applied job remains accessible in Application Tracker."""
        temp_storage.mark_as_applied(target_java_job.id)

        apps = temp_storage.list_applications()
        assert len(apps) == 1
        assert apps[0].job_id == target_java_job.id
        assert apps[0].status == ApplicationStatus.APPLIED

    def test_3_applied_job_remains_accessible_in_all_jobs(self, temp_storage, target_java_job):
        """3. An Applied job remains accessible in All Jobs."""
        temp_storage.mark_as_applied(target_java_job.id)

        all_jobs = temp_storage.list_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0].id == target_java_job.id
        assert all_jobs[0].applied_at is not None

    def test_4_assessment_status_excluded_from_active_recommendations(self, temp_storage, target_java_job):
        """4. A job with Assessment status is excluded from active recommendations."""
        app = Application(job_id=target_java_job.id, status=ApplicationStatus.ASSESSMENT)
        temp_storage.create_application(app)

        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_5_interview_status_excluded_from_active_recommendations(self, temp_storage, target_java_job):
        """5. A job with Interview status is excluded from active recommendations."""
        app = Application(job_id=target_java_job.id, status=ApplicationStatus.INTERVIEW)
        temp_storage.create_application(app)

        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_6_offer_status_excluded_from_active_recommendations(self, temp_storage, target_java_job):
        """6. A job with Offer status is excluded from active recommendations."""
        app = Application(job_id=target_java_job.id, status=ApplicationStatus.OFFER)
        temp_storage.create_application(app)

        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_7_rejected_status_excluded_from_active_recommendations(self, temp_storage, target_java_job):
        """7. A Rejected application is excluded from active recommendations."""
        app = Application(job_id=target_java_job.id, status=ApplicationStatus.REJECTED)
        temp_storage.create_application(app)

        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_8_withdrawn_status_excluded_from_active_recommendations(self, temp_storage, target_java_job):
        """8. A Withdrawn application is excluded from active recommendations."""
        app = Application(job_id=target_java_job.id, status=ApplicationStatus.WITHDRAWN)
        temp_storage.create_application(app)

        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_9_dismissed_job_excluded_from_active_recommendations(self, temp_storage, target_java_job):
        """9. A Dismissed job is excluded from active recommendations."""
        temp_storage.update_review_state(target_java_job.id, "DISMISSED")

        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id not in all_rec_ids

    def test_10_unapplied_undismissed_job_appears_normally(self, temp_storage, target_java_job):
        """10. A job with no application and no dismissal can still appear normally."""
        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()
        all_rec_ids = {r.job.id for sec in recs.values() for r in sec}
        assert target_java_job.id in all_rec_ids

    def test_11_mutually_exclusive_display_queues(self, temp_storage, target_java_job, fast_cash_job):
        """11. The same job cannot appear in two primary recommendation sections."""
        query_svc = JobQueryService(storage=temp_storage)
        recs = query_svc.get_dashboard_recommendations()

        apply_first_ids = {r.job.id for r in recs["apply_first"]}
        fast_cash_ids = {r.job.id for r in recs["fastest_cash"]}
        tech_match_ids = {r.job.id for r in recs["best_technical_match"]}
        long_term_ids = {r.job.id for r in recs["best_long_term"]}
        new_today_ids = {r.job.id for r in recs["new_today"]}

        # Check pairwise disjointness across display sections
        all_sections = [apply_first_ids, fast_cash_ids, tech_match_ids, long_term_ids, new_today_ids]
        for i in range(len(all_sections)):
            for j in range(i + 1, len(all_sections)):
                overlap = all_sections[i].intersection(all_sections[j])
                assert len(overlap) == 0, f"Section overlap found: {overlap}"

    def test_12_cross_source_ingestion_deduplication_works(self, temp_storage):
        """12. Cross-source ingestion deduplication still works."""
        dedup = JobDeduplicator(storage=temp_storage)
        job_a = NormalizedJob(
            id="job-dup-1",
            source_name="remotive",
            external_id="ext-dup-1",
            url="https://example.com/job/dup-1",
            title="Senior Backend Engineer",
            company_name="Duplicate Corp",
            is_remote=True,
            location_requirement="Worldwide",
            canonical_fingerprint="fingerprint-dup-unique",
            posted_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )
        temp_storage.save_normalized_job(job_a)

        job_b = NormalizedJob(
            id="job-dup-2",
            source_name="jobicy",
            external_id="ext-dup-2",
            url="https://example.com/job/dup-1",  # Same URL -> duplicate
            title="Senior Backend Engineer",
            company_name="Duplicate Corp",
            is_remote=True,
            location_requirement="Worldwide",
            canonical_fingerprint="fingerprint-dup-unique",
            posted_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )

        res = dedup.check_duplicate(job_b)
        assert res.is_duplicate is True
        assert res.match_level == "URL"
        assert res.existing_job_id == "job-dup-1"


    def test_13_mark_as_applied_persists_correctly(self, temp_storage, target_java_job):
        """13. Mark as Applied persists correctly."""
        temp_storage.mark_as_applied(target_java_job.id)

        # Verify database record
        updated_job = temp_storage.get_job_by_id(target_java_job.id)
        assert updated_job is not None
        assert updated_job.applied_at is not None

        app = temp_storage.get_application_by_job_id(target_java_job.id)
        assert app is not None
        assert app.status == ApplicationStatus.APPLIED

    def test_14_dismiss_persists_correctly(self, temp_storage, target_java_job):
        """14. Dismiss persists correctly."""
        temp_storage.update_review_state(target_java_job.id, "DISMISSED")

        updated_job = temp_storage.get_job_by_id(target_java_job.id)
        assert updated_job is not None
        assert updated_job.review_state == "DISMISSED"

    def test_15_reviewing_persists_correctly(self, temp_storage, target_java_job):
        """15. Reviewing persists correctly."""
        temp_storage.update_review_state(target_java_job.id, "REVIEWING")

        updated_job = temp_storage.get_job_by_id(target_java_job.id)
        assert updated_job is not None
        assert updated_job.review_state == "REVIEWING"

    def test_16_existing_application_analytics_remain_correct(self, temp_storage, target_java_job, fast_cash_job):
        """16. Existing application analytics remain correct."""
        temp_storage.mark_as_applied(target_java_job.id)

        summary = temp_storage.get_analytics_summary()
        assert summary["total_applications"] == 1
        assert summary["applied"] == 1
        assert summary["awaiting_response"] == 1

        full = temp_storage.get_full_analytics()
        assert "summary" in full
        assert "daily_activity_7d" in full
        assert "funnel" in full
        assert "sources" in full

    def test_17_existing_application_status_history_remains_correct(self, temp_storage, target_java_job):
        """17. Existing application status history remains correct."""
        temp_storage.mark_as_applied(target_java_job.id)
        app = temp_storage.get_application_by_job_id(target_java_job.id)
        assert app is not None

        # Update application status to INTERVIEW
        temp_storage.update_application(
            app_id=app.id,
            status=ApplicationStatus.INTERVIEW,
            interview_stage=InterviewStage.STAGE_2,
        )

        history = temp_storage.get_status_history(app.id)
        assert len(history) == 2
        assert history[0].status == ApplicationStatus.APPLIED
        assert history[1].status == ApplicationStatus.INTERVIEW
        assert history[1].interview_stage == InterviewStage.STAGE_2

    def test_18_existing_excel_export_remains_correct(self, temp_storage, target_java_job):
        """18. Existing Excel export remains correct."""
        temp_storage.mark_as_applied(target_java_job.id)
        query_svc = JobQueryService(storage=temp_storage)

        exporter = ExcelExporter(storage=temp_storage, query_service=query_svc)
        excel_bytes = exporter.generate_workbook_bytes()

        assert excel_bytes is not None
        assert len(excel_bytes) > 0
        # Openpyxl PK zip header check
        assert excel_bytes.startswith(b"PK\x03\x04")

    def test_19_api_endpoints_action_responses(self, temp_storage, target_java_job):
        """Tests API responses for review_state, apply_intent, and dashboard endpoints."""
        server = DashboardServer(host="127.0.0.1", port=8595, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # 1. POST /api/jobs/<job_id>/review_state -> REVIEWING
            url_review = f"http://127.0.0.1:8595/api/jobs/{target_java_job.id}/review_state"
            data = json.dumps({"review_state": "REVIEWING"}).encode("utf-8")
            req = urllib.request.Request(url_review, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                assert res_data["success"] is True
                assert res_data["review_state"] == "REVIEWING"

            # 2. POST /api/jobs/<job_id>/apply_intent
            url_apply = f"http://127.0.0.1:8595/api/jobs/{target_java_job.id}/apply_intent"
            data = json.dumps({"applied": True}).encode("utf-8")
            req = urllib.request.Request(url_apply, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                assert res_data["success"] is True
                assert res_data["job_id"] == target_java_job.id
                assert res_data["application"]["status"] == "APPLIED"

            # 3. GET /api/dashboard -> Job is removed from active dashboard recommendation sections
            with urllib.request.urlopen("http://127.0.0.1:8595/api/dashboard") as resp:
                dash = json.loads(resp.read().decode("utf-8"))
                all_rec_ids = {r["job"]["id"] for sec in dash.values() for r in sec}
                assert target_java_job.id not in all_rec_ids

            # 4. GET /api/applications -> Application is present
            with urllib.request.urlopen("http://127.0.0.1:8595/api/applications") as resp:
                apps = json.loads(resp.read().decode("utf-8"))
                assert len(apps) == 1
                assert apps[0]["job_id"] == target_java_job.id

        finally:
            server.stop()
