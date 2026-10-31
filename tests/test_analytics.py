"""Unit and integration tests for Phase 8 — Application Analytics and Job Search Funnel."""

import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
import urllib.request
import json

from job_monitor.db.storage import JobStorage
from job_monitor.models.normalized_job import NormalizedJob
from job_monitor.models.application import Application, ApplicationStatus, InterviewStage, ApplicationStatusHistory
from job_monitor.dashboard.server import DashboardServer


@pytest.fixture
def temp_storage():
    """Provides a fresh temporary SQLite storage instance per test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    storage = JobStorage(db_path=db_path)
    yield storage

    if os.path.exists(db_path):
        os.remove(db_path)


class TestApplicationAnalytics:
    def test_empty_database_analytics(self, temp_storage):
        """Tests analytics calculations against an empty database."""
        summary = temp_storage.get_analytics_summary()
        assert summary["total_applications"] == 0
        assert summary["applications_today"] == 0
        assert summary["applications_yesterday"] == 0
        assert summary["applications_7_days"] == 0
        assert summary["applications_30_days"] == 0
        assert summary["awaiting_response"] == 0
        assert summary["applied"] == 0

        daily = temp_storage.get_daily_analytics(days=7)
        assert len(daily) == 7
        assert all(d["count"] == 0 for d in daily)

        weekly = temp_storage.get_weekly_summary()
        assert weekly["this_week"]["applications"] == 0
        assert weekly["previous_week"]["applications"] == 0
        assert weekly["volume_change_pct"] is None
        assert weekly["has_sufficient_history"] is False

        funnel = temp_storage.get_funnel_analytics()
        assert funnel["funnel_counts"]["applications"] == 0
        assert funnel["conversion_rates"]["app_to_interview_pct"] == 0.0
        assert funnel["conversion_rates"]["interview_to_offer_pct"] is None
        assert funnel["formatted_rates"]["app_to_interview"] == "Historical transition data unavailable"

        sources = temp_storage.get_source_analytics()
        assert sources == []

        categories = temp_storage.get_category_analytics()
        assert categories == []

        next_act = temp_storage.get_next_actions_analytics()
        assert next_act["overdue"] == []
        assert next_act["due_today"] == []
        assert next_act["due_next_7_days"] == []

    def test_single_application_analytics(self, temp_storage):
        """Tests analytics for a single application created today."""
        job = NormalizedJob(
            id="job-single",
            source_name="remotive",
            external_id="ext-single",
            url="https://example.com/job/single",
            title="Python Developer",
            company_name="Single Corp",
            category="Backend / Software Engineering",
            fetched_at=datetime.now(timezone.utc),
        )
        temp_storage.save_normalized_job(job)

        app = Application(
            job_id=job.id,
            status=ApplicationStatus.APPLIED,
            applied_at=datetime.now(timezone.utc),
        )
        created = temp_storage.create_application(app)

        summary = temp_storage.get_analytics_summary()
        assert summary["total_applications"] == 1
        assert summary["applications_today"] == 1
        assert summary["awaiting_response"] == 1
        assert summary["applied"] == 1

        sources = temp_storage.get_source_analytics()
        assert len(sources) == 1
        assert sources[0]["source_name"] == "remotive"
        assert sources[0]["applications"] == 1

        categories = temp_storage.get_category_analytics()
        assert len(categories) == 1
        assert categories[0]["category"] == "Backend / Software Engineering"
        assert categories[0]["applications"] == 1

    def test_multiple_applications_time_ranges_and_counts(self, temp_storage):
        """Tests top-level metrics across today, yesterday, 7-day, and 30-day time windows."""
        now = datetime.now(timezone.utc)
        today_time = now
        yesterday_time = now - timedelta(days=1)
        days_5_ago = now - timedelta(days=5)
        days_20_ago = now - timedelta(days=20)
        days_40_ago = now - timedelta(days=40)

        times = [today_time, yesterday_time, days_5_ago, days_20_ago, days_40_ago]
        for i, t in enumerate(times):
            j = NormalizedJob(
                id=f"job-t-{i}",
                source_name="jobicy",
                external_id=f"ext-t-{i}",
                url=f"https://example.com/job/{i}",
                title=f"Dev {i}",
                company_name=f"Co {i}",
                fetched_at=t,
            )
            temp_storage.save_normalized_job(j)

            app = Application(
                job_id=j.id,
                status=ApplicationStatus.APPLIED,
                applied_at=t,
            )
            temp_storage.create_application(app)

        summary = temp_storage.get_analytics_summary()
        assert summary["total_applications"] == 5
        assert summary["applications_today"] == 1
        assert summary["applications_yesterday"] == 1
        assert summary["applications_7_days"] == 3  # today, yesterday, 5 days ago
        assert summary["applications_30_days"] == 4  # plus 20 days ago

    def test_status_breakdown_and_awaiting_response_definition(self, temp_storage):
        """Tests current status counts and verifies 'Awaiting Response' excludes REJECTED, WITHDRAWN, ACCEPTED, and OFFER."""
        statuses = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.ASSESSMENT,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.ACCEPTED,
        ]

        for i, st in enumerate(statuses):
            j = NormalizedJob(
                id=f"job-st-{i}",
                source_name="weworkremotely",
                external_id=f"ext-st-{i}",
                url=f"https://example.com/job/st-{i}",
                title=f"Role {i}",
                company_name=f"Corp {i}",
                fetched_at=datetime.now(timezone.utc),
            )
            temp_storage.save_normalized_job(j)

            app = Application(
                job_id=j.id,
                status=st,
                applied_at=datetime.now(timezone.utc),
            )
            temp_storage.create_application(app)

        summary = temp_storage.get_analytics_summary()
        assert summary["total_applications"] == 7
        assert summary["applied"] == 1
        assert summary["assessments"] == 1
        assert summary["interviews"] == 1
        assert summary["offers"] == 1
        assert summary["rejections"] == 1
        assert summary["withdrawn"] == 1
        assert summary["accepted"] == 1

        # Awaiting response: APPLIED, ASSESSMENT, INTERVIEW (3 total active)
        assert summary["awaiting_response"] == 3

    def test_daily_activity_timeline_ranges(self, temp_storage):
        """Tests daily application activity timeline generation for 7 and 30 day ranges."""
        now = datetime.now(timezone.utc)
        # Create 2 applications yesterday, 1 today
        for i in range(2):
            j = NormalizedJob(
                id=f"job-d-{i}",
                source_name="test",
                external_id=f"ext-d-{i}",
                url=f"https://example.com/job/d-{i}",
                title=f"Job {i}",
                company_name="Test Co",
                fetched_at=now - timedelta(days=1),
            )
            temp_storage.save_normalized_job(j)
            temp_storage.create_application(Application(job_id=j.id, applied_at=now - timedelta(days=1)))

        j_today = NormalizedJob(
            id="job-d-today",
            source_name="test",
            external_id="ext-d-today",
            url="https://example.com/job/d-today",
            title="Today Job",
            company_name="Test Co",
            fetched_at=now,
        )
        temp_storage.save_normalized_job(j_today)
        temp_storage.create_application(Application(job_id=j_today.id, applied_at=now))

        daily_7 = temp_storage.get_daily_analytics(days=7)
        assert len(daily_7) == 7
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        today_entry = next(d for d in daily_7 if d["date"] == today_str)
        yesterday_entry = next(d for d in daily_7 if d["date"] == yesterday_str)

        assert today_entry["count"] == 1
        assert yesterday_entry["count"] == 2

    def test_weekly_comparison_and_percentage_change(self, temp_storage):
        """Tests weekly job-search summary and volume percentage change calculation."""
        now = datetime.now(timezone.utc)

        # 4 applications this week (last 7 days)
        for i in range(4):
            j = NormalizedJob(
                id=f"job-tw-{i}",
                source_name="test",
                external_id=f"ext-tw-{i}",
                url=f"https://example.com/job/tw-{i}",
                title=f"Role {i}",
                company_name="Company TW",
                fetched_at=now - timedelta(days=2),
            )
            temp_storage.save_normalized_job(j)
            temp_storage.create_application(Application(job_id=j.id, applied_at=now - timedelta(days=2)))

        # 2 applications previous week (days 8 to 13 ago)
        for i in range(2):
            j = NormalizedJob(
                id=f"job-pw-{i}",
                source_name="test",
                external_id=f"ext-pw-{i}",
                url=f"https://example.com/job/pw-{i}",
                title=f"Prev Role {i}",
                company_name="Company PW",
                fetched_at=now - timedelta(days=10),
            )
            temp_storage.save_normalized_job(j)
            temp_storage.create_application(Application(job_id=j.id, applied_at=now - timedelta(days=10)))

        weekly = temp_storage.get_weekly_summary()
        assert weekly["this_week"]["applications"] == 4
        assert weekly["previous_week"]["applications"] == 2
        # (4 - 2) / 2 * 100 = 100.0%
        assert weekly["volume_change_pct"] == 100.0
        assert weekly["has_sufficient_history"] is True

    def test_status_history_creation_updates_and_migration(self, temp_storage):
        """Tests status history table logging, status updates, and auto-migration of baseline records."""
        j = NormalizedJob(
            id="job-hist-1",
            source_name="remotive",
            external_id="ext-hist-1",
            url="https://example.com/job/hist-1",
            title="Senior Architect",
            company_name="Tech Solutions",
            fetched_at=datetime.now(timezone.utc),
        )
        temp_storage.save_normalized_job(j)

        # 1. Create Application -> should insert initial history entry (APPLIED)
        app = Application(job_id=j.id, status=ApplicationStatus.APPLIED)
        created_app, _ = temp_storage.create_application(app)
        assert created_app.id is not None

        history_1 = temp_storage.get_status_history(created_app.id)
        assert len(history_1) == 1
        assert history_1[0].status == ApplicationStatus.APPLIED

        # 2. Update Application Status to INTERVIEW -> should insert second history entry
        updated_app = temp_storage.update_application(
            created_app.id,
            status=ApplicationStatus.INTERVIEW,
            interview_stage=InterviewStage.STAGE_1,
        )
        assert updated_app.status == ApplicationStatus.INTERVIEW

        history_2 = temp_storage.get_status_history(created_app.id)
        assert len(history_2) == 2
        assert history_2[1].status == ApplicationStatus.INTERVIEW
        assert history_2[1].interview_stage == InterviewStage.STAGE_1

        # 3. Verify auto-migration for baseline existing applications without duplicate history creation
        j_legacy = NormalizedJob(
            id="job-legacy-1",
            source_name="remotive",
            external_id="ext-legacy-1",
            url="https://example.com/job/legacy-1",
            title="Legacy Architect",
            company_name="Legacy Corp",
            fetched_at=datetime.now(timezone.utc),
        )
        temp_storage.save_normalized_job(j_legacy)

        with temp_storage.get_connection() as conn:
            # Manually insert an application row directly into database without history
            conn.cursor().execute(
                "INSERT INTO applications (id, job_id, status, applied_at, interview_stage) VALUES (?, ?, ?, ?, ?)",
                ("app-legacy-1", j_legacy.id, "ASSESSMENT", datetime.now(timezone.utc).isoformat(), "NONE")
            )
            conn.commit()

        # Re-initialize DB or call init_db to trigger safe migration
        temp_storage.init_db()

        legacy_hist = temp_storage.get_status_history("app-legacy-1")
        assert len(legacy_hist) == 1
        assert legacy_hist[0].status == ApplicationStatus.ASSESSMENT

    def test_funnel_and_conversion_rates(self, temp_storage):
        """Tests funnel lifecycle tracking and conversion rates calculation, including zero-denominator handling."""
        # 10 applications:
        # - 5 reach ASSESSMENT
        # - 3 reach INTERVIEW
        # - 1 reaches OFFER
        # - 1 reaches ACCEPTED
        for i in range(10):
            j = NormalizedJob(
                id=f"job-funnel-{i}",
                source_name="remotive",
                external_id=f"ext-funnel-{i}",
                url=f"https://example.com/job/funnel-{i}",
                title=f"Dev {i}",
                company_name="Corp",
                fetched_at=datetime.now(timezone.utc),
            )
            temp_storage.save_normalized_job(j)

            status = ApplicationStatus.APPLIED
            if i < 5:
                status = ApplicationStatus.ASSESSMENT
            if i < 3:
                status = ApplicationStatus.INTERVIEW
            if i == 1:
                status = ApplicationStatus.OFFER
            if i == 0:
                status = ApplicationStatus.ACCEPTED

            app, _ = temp_storage.create_application(Application(job_id=j.id, status=ApplicationStatus.APPLIED))
            if status != ApplicationStatus.APPLIED:
                temp_storage.update_application(app.id, status=status)

        funnel = temp_storage.get_funnel_analytics()
        fc = funnel["funnel_counts"]
        assert fc["applications"] == 10
        assert fc["assessments"] == 5
        assert fc["interviews"] == 3
        assert fc["offers"] == 2  # OFFER + ACCEPTED
        assert fc["accepted"] == 1

        cr = funnel["conversion_rates"]
        assert cr["app_to_assessment_pct"] == 50.0
        assert cr["app_to_interview_pct"] == 30.0
        assert cr["app_to_offer_pct"] == 20.0
        assert cr["interview_to_offer_pct"] == 66.7
        assert cr["offer_to_accepted_pct"] == 50.0

        fr = funnel["formatted_rates"]
        assert "50.0% (5 of 10 applications)" in fr["app_to_assessment"]
        assert "30.0% (3 of 10 applications)" in fr["app_to_interview"]

    def test_source_and_category_performance_with_missing_fields(self, temp_storage):
        """Tests source and category analytics, including handling of missing/blank categories or sources."""
        j1 = NormalizedJob(
            id="job-sc-1",
            source_name="remotive",
            external_id="ext-sc-1",
            url="https://example.com/job/sc-1",
            title="Backend Dev",
            company_name="Remotive Co",
            category="Backend / Software Engineering",
            fetched_at=datetime.now(timezone.utc),
        )
        j2 = NormalizedJob(
            id="job-sc-2",
            source_name="jobicy",
            external_id="ext-sc-2",
            url="https://example.com/job/sc-2",
            title="Data Analyst",
            company_name="Jobicy Co",
            category="",  # Missing category fallback
            fetched_at=datetime.now(timezone.utc),
        )
        temp_storage.save_normalized_job(j1)
        temp_storage.save_normalized_job(j2)

        app1, _ = temp_storage.create_application(Application(job_id=j1.id, status=ApplicationStatus.APPLIED))
        temp_storage.update_application(app1.id, status=ApplicationStatus.INTERVIEW)

        app2, _ = temp_storage.create_application(Application(job_id=j2.id, status=ApplicationStatus.APPLIED))

        sources = temp_storage.get_source_analytics()
        assert len(sources) == 2
        remotive_src = next(s for s in sources if s["source_name"] == "remotive")
        assert remotive_src["applications"] == 1
        assert remotive_src["interviews"] == 1
        assert remotive_src["interview_rate_pct"] == 100.0

        categories = temp_storage.get_category_analytics()
        assert len(categories) == 2
        # Check fallback category name for empty category
        fallback_cat = next(c for c in categories if c["category"] == "Software Engineering")
        assert fallback_cat["applications"] == 1

    def test_next_actions_categorization(self, temp_storage):
        """Tests next actions grouping into Overdue, Due Today, and Due in Next 7 Days."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        next_3_str = (now + timedelta(days=3)).strftime("%Y-%m-%d")

        data = [
            ("Overdue Action", yesterday_str),
            ("Today Action", today_str),
            ("Upcoming Action", next_3_str),
        ]

        for i, (action, act_date) in enumerate(data):
            j = NormalizedJob(
                id=f"job-na-{i}",
                source_name="test",
                external_id=f"ext-na-{i}",
                url=f"https://example.com/job/na-{i}",
                title=f"Action Job {i}",
                company_name="Action Corp",
                fetched_at=now,
            )
            temp_storage.save_normalized_job(j)

            app = Application(
                job_id=j.id,
                status=ApplicationStatus.INTERVIEW,
                next_action=action,
                next_action_date=act_date,
            )
            temp_storage.create_application(app)

        next_actions = temp_storage.get_next_actions_analytics()
        assert len(next_actions["overdue"]) == 1
        assert next_actions["overdue"][0]["next_action"] == "Overdue Action"

        assert len(next_actions["due_today"]) == 1
        assert next_actions["due_today"][0]["next_action"] == "Today Action"

        assert len(next_actions["due_next_7_days"]) == 1
        assert next_actions["due_next_7_days"][0]["next_action"] == "Upcoming Action"


class TestAnalyticsRESTAPI:
    def test_analytics_api_endpoints(self, temp_storage):
        """Tests REST API endpoints for analytics (/api/analytics/*)."""
        server = DashboardServer(host="127.0.0.1", port=8598, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # Populate sample application
            j = NormalizedJob(
                id="job-api-1",
                source_name="remotive",
                external_id="ext-api-1",
                url="https://example.com/job/api-1",
                title="Python API Eng",
                company_name="API Co",
                category="Backend / Software Engineering",
                fetched_at=datetime.now(timezone.utc),
            )
            temp_storage.save_normalized_job(j)
            temp_storage.create_application(Application(job_id=j.id, status=ApplicationStatus.APPLIED))

            base_url = "http://127.0.0.1:8598"

            # 1. GET /api/analytics/all
            req = urllib.request.urlopen(f"{base_url}/api/analytics/all")
            assert req.status == 200
            all_data = json.loads(req.read().decode())
            assert "summary" in all_data
            assert "funnel" in all_data
            assert all_data["summary"]["total_applications"] == 1

            # 2. GET /api/analytics/summary
            req = urllib.request.urlopen(f"{base_url}/api/analytics/summary")
            assert req.status == 200
            summary = json.loads(req.read().decode())
            assert summary["total_applications"] == 1

            # 3. GET /api/analytics/daily?days=7
            req = urllib.request.urlopen(f"{base_url}/api/analytics/daily?days=7")
            assert req.status == 200
            daily = json.loads(req.read().decode())
            assert len(daily) == 7

            # 4. GET /api/analytics/funnel
            req = urllib.request.urlopen(f"{base_url}/api/analytics/funnel")
            assert req.status == 200
            funnel = json.loads(req.read().decode())
            assert funnel["funnel_counts"]["applications"] == 1

            # 5. GET /api/analytics/sources
            req = urllib.request.urlopen(f"{base_url}/api/analytics/sources")
            assert req.status == 200
            sources = json.loads(req.read().decode())
            assert len(sources) == 1
            assert sources[0]["source_name"] == "remotive"

            # 6. GET /api/analytics/next-actions
            req = urllib.request.urlopen(f"{base_url}/api/analytics/next-actions")
            assert req.status == 200
            next_act = json.loads(req.read().decode())
            assert "overdue" in next_act

        finally:
            server.stop()
