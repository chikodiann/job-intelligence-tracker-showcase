import json
import sqlite3
import uuid
import urllib.request
import pytest
from datetime import datetime, timezone

from job_monitor.dashboard.server import DashboardServer
from job_monitor.db.storage import JobStorage
from job_monitor.models.application import Application, ApplicationStatus, InterviewStage
from job_monitor.models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod


@pytest.fixture
def temp_storage(tmp_path):
    """Fixture providing temporary SQLite storage."""
    db_file = str(tmp_path / "test_applications.db")
    storage = JobStorage(db_path=db_file)
    return storage


@pytest.fixture
def sample_job(temp_storage):
    """Fixture inserting a sample job into temp storage."""
    job = NormalizedJob(
        id="job-app-1",
        source_name="remotive",
        external_id="ext-app-1",
        url="https://remotive.com/job/app1",
        title="Full Stack Engineer",
        company_name="Acme Tech",
        is_remote=True,
        location_requirement="Worldwide",
        employment_type=EmploymentType.FULL_TIME,
        salary_min=100000,
        salary_max=140000,
        salary_currency="USD",
        salary_period=SalaryPeriod.ANNUAL,
        annualized_min_usd=100000,
        annualized_max_usd=140000,
        original_salary_text="$100k - $140k",
        category="Software Development",
        tags=["python", "react"],
        description_raw="<p>Looking for a Full Stack engineer.</p>",
        description_text="Looking for a Full Stack engineer.",
        content_hash="hash-app-1",
        canonical_fingerprint="fingerprint-app-1",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )
    temp_storage.save_normalized_job(job)
    return job


class TestApplicationStorage:
    def test_create_and_get_application(self, temp_storage, sample_job):
        """Tests creating a new Application record and retrieving it by ID and job_id."""
        app = Application(
            job_id=sample_job.id,
            status=ApplicationStatus.APPLIED,
            interview_stage=InterviewStage.NONE,
            notes="Submitted resume via portal",
        )
        created, is_new = temp_storage.create_application(app)
        assert is_new is True
        assert created.id is not None
        assert created.job_id == sample_job.id
        assert created.status == ApplicationStatus.APPLIED

        # Retrieve by ID
        by_id = temp_storage.get_application_by_id(created.id)
        assert by_id is not None
        assert by_id.job_id == sample_job.id

        # Retrieve by Job ID
        by_job = temp_storage.get_application_by_job_id(sample_job.id)
        assert by_job is not None
        assert by_job.id == created.id

    def test_duplicate_prevention(self, temp_storage, sample_job):
        """Tests that attempting to create duplicate application for same job returns existing."""
        app1 = Application(job_id=sample_job.id, status=ApplicationStatus.APPLIED)
        created1, is_new1 = temp_storage.create_application(app1)
        assert is_new1 is True

        app2 = Application(job_id=sample_job.id, status=ApplicationStatus.INTERVIEW)
        created2, is_new2 = temp_storage.create_application(app2)
        assert is_new2 is False
        assert created2.id == created1.id
        assert created2.status == ApplicationStatus.APPLIED  # Retains original status

    def test_mark_as_applied(self, temp_storage, sample_job):
        """Tests marking a job as applied via storage helper."""
        assert temp_storage.get_application_by_job_id(sample_job.id) is None
        success = temp_storage.mark_as_applied(sample_job.id)
        assert success is True

        app = temp_storage.get_application_by_job_id(sample_job.id)
        assert app is not None
        assert app.status == ApplicationStatus.APPLIED

    def test_update_application_status_and_stage(self, temp_storage, sample_job):
        """Tests updating status, interview stage, next action date, and notes."""
        app = Application(job_id=sample_job.id, status=ApplicationStatus.APPLIED)
        created, _ = temp_storage.create_application(app)

        # Update to ASSESSMENT
        updated = temp_storage.update_application(
            created.id,
            status=ApplicationStatus.ASSESSMENT,
            next_action="Complete take-home test",
            next_action_date="2026-10-15",
            notes="Take-home assignment received",
        )
        assert updated.status == ApplicationStatus.ASSESSMENT
        assert updated.next_action == "Complete take-home test"
        assert updated.next_action_date == "2026-10-15"

        # Update to INTERVIEW / STAGE_1
        updated = temp_storage.update_application(
            created.id,
            status=ApplicationStatus.INTERVIEW,
            interview_stage=InterviewStage.STAGE_1,
            next_action="Prepare for technical interview",
            next_action_date="2026-10-20",
        )
        assert updated.status == ApplicationStatus.INTERVIEW
        assert updated.interview_stage == InterviewStage.STAGE_1

    def test_migration_from_existing_jobs_applied_at(self, tmp_path):
        """Tests auto-migration of jobs with pre-existing applied_at timestamps."""
        db_file = str(tmp_path / "migration_test.db")
        conn = sqlite3.connect(db_file)
        # Create legacy jobs table without applications table
        conn.execute("""
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            source_name TEXT,
            external_id TEXT,
            url TEXT,
            title TEXT,
            company_name TEXT,
            is_remote INTEGER,
            location_requirement TEXT,
            employment_type TEXT,
            salary_min REAL,
            salary_max REAL,
            salary_currency TEXT,
            salary_period TEXT,
            annualized_min_usd REAL,
            annualized_max_usd REAL,
            original_salary_text TEXT,
            category TEXT,
            tags TEXT,
            description_raw TEXT,
            description_text TEXT,
            content_hash TEXT,
            canonical_fingerprint TEXT,
            posted_at TEXT,
            fetched_at TEXT,
            first_seen_at TEXT,
            last_seen_at TEXT,
            last_verified_at TEXT,
            status TEXT,
            review_state TEXT DEFAULT 'UNREVIEWED',
            applied_at TEXT
        )
        """)
        # Insert a job with applied_at
        applied_time = "2026-10-01T12:00:00+00:00"
        conn.execute(
            "INSERT INTO jobs (id, source_name, external_id, title, company_name, fetched_at, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("job-legacy-1", "remotive", "ext-leg-1", "Legacy Dev", "Legacy Inc", "2026-10-01T10:00:00+00:00", applied_time)
        )
        conn.commit()
        conn.close()

        # Initialize JobStorage on the database
        storage = JobStorage(db_path=db_file)
        app = storage.get_application_by_job_id("job-legacy-1")
        assert app is not None
        assert app.job_id == "job-legacy-1"
        assert app.status == ApplicationStatus.APPLIED
        assert app.applied_at.isoformat() == applied_time

    def test_empty_application_tracker(self, temp_storage):
        """Tests listing applications and counts on an empty database."""
        apps = temp_storage.list_applications()
        assert apps == []

        counts = temp_storage.count_applications_summary()
        assert counts["total_applications"] == 0
        assert counts["awaiting_response"] == 0
        assert counts["interviews"] == 0
        assert counts["offers"] == 0
        assert counts["rejections"] == 0

    def test_multiple_applications_across_different_jobs(self, temp_storage):
        """Tests managing multiple applications across different jobs."""
        for i in range(5):
            j = NormalizedJob(
                id=f"job-multi-{i}",
                source_name="test",
                external_id=f"ext-multi-{i}",
                url=f"https://example.com/job/{i}",
                title=f"Engineer {i}",
                company_name=f"Company {i}",
                fetched_at=datetime.now(timezone.utc),
            )
            temp_storage.save_normalized_job(j)

        statuses = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.ASSESSMENT,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
        ]

        for i, status in enumerate(statuses):
            app = Application(
                job_id=f"job-multi-{i}",
                status=status,
                interview_stage=InterviewStage.STAGE_2 if status == ApplicationStatus.INTERVIEW else InterviewStage.NONE,
            )
            temp_storage.create_application(app)

        all_apps = temp_storage.list_applications()
        assert len(all_apps) == 5

        counts = temp_storage.count_applications_summary()
        assert counts["total_applications"] == 5
        assert counts["awaiting_response"] == 3
        assert counts["interviews"] == 1
        assert counts["offers"] == 1
        assert counts["rejections"] == 1


class TestApplicationRESTAPI:
    def test_application_api_workflow(self, temp_storage, sample_job):
        """Tests complete REST API workflow for applications."""
        server = DashboardServer(host="127.0.0.1", port=8590, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # 1. Get summary - 0 applications
            with urllib.request.urlopen("http://127.0.0.1:8590/api/summary") as resp:
                summary = json.loads(resp.read().decode("utf-8"))
                assert summary["total_applications"] == 0

            # 2. Mark as applied via apply_intent API
            body = json.dumps({"applied": True}).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:8590/api/jobs/{sample_job.id}/apply_intent",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                assert res["success"] is True

            # 3. List applications API
            with urllib.request.urlopen("http://127.0.0.1:8590/api/applications") as resp:
                apps = json.loads(resp.read().decode("utf-8"))
                assert len(apps) == 1
                app_id = apps[0]["id"]
                assert apps[0]["status"] == "APPLIED"
                assert apps[0]["job"]["title"] == "Full Stack Engineer"

            # 4. Update status to ASSESSMENT via POST /api/applications/<app_id>
            body = json.dumps({
                "status": "ASSESSMENT",
                "next_action": "Complete technical assessment",
                "next_action_date": "2026-10-12",
                "notes": "Code challenge link received."
            }).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:8590/api/applications/{app_id}",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                assert res["success"] is True
                assert res["application"]["status"] == "ASSESSMENT"

            # 5. Update to INTERVIEW / STAGE_1
            body = json.dumps({
                "status": "INTERVIEW",
                "interview_stage": "STAGE_1",
                "next_action": "Prep system design questions",
                "notes": "Stage 1 call scheduled with lead engineer."
            }).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:8590/api/applications/{app_id}",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                assert res["success"] is True
                assert res["application"]["status"] == "INTERVIEW"
                assert res["application"]["interview_stage"] == "STAGE_1"

            # 6. Verify summary updated
            with urllib.request.urlopen("http://127.0.0.1:8590/api/summary") as resp:
                summary = json.loads(resp.read().decode("utf-8"))
                assert summary["total_applications"] == 1
                assert summary["interviews"] == 1

        finally:
            server.stop()
