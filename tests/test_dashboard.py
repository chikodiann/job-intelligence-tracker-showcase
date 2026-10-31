import json
import urllib.request
import pytest
from datetime import datetime, timezone

from job_monitor.dashboard.server import DashboardServer
from job_monitor.db.storage import JobStorage
from job_monitor.models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod


@pytest.fixture
def temp_storage(tmp_path):
    """Fixture providing temporary SQLite storage."""
    db_file = str(tmp_path / "test_jobs.db")
    storage = JobStorage(db_path=db_file)
    return storage


@pytest.fixture
def sample_jobs(temp_storage):
    """Fixture inserting sample jobs into temp storage."""
    job1 = NormalizedJob(
        id="job-111",
        source_name="remotive",
        external_id="ext-1",
        url="https://remotive.com/job/111",
        title="Senior Java Backend Engineer",
        company_name="Acme Tech",
        is_remote=True,
        location_requirement="Worldwide",
        employment_type=EmploymentType.FULL_TIME,
        salary_min=100000,
        salary_max=130000,
        salary_currency="USD",
        salary_period=SalaryPeriod.ANNUAL,
        annualized_min_usd=100000,
        annualized_max_usd=130000,
        original_salary_text="$100k - $130k",
        category="Software Development",
        tags=["java", "spring boot", "postgres"],
        description_raw="<p>Looking for a Java Spring Boot developer. Worldwide remote.</p>",
        description_text="Looking for a Java Spring Boot developer. Worldwide remote.",
        content_hash="hash-111",
        canonical_fingerprint="fingerprint-111",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )

    job2 = NormalizedJob(
        id="job-222",
        source_name="jobicy",
        external_id="ext-2",
        url="https://jobicy.com/job/222",
        title="Go API Developer",
        company_name="Fast Cloud",
        is_remote=True,
        location_requirement="EMEA",
        employment_type=EmploymentType.CONTRACT,
        salary_min=60,
        salary_max=80,
        salary_currency="USD",
        salary_period=SalaryPeriod.HOURLY,
        annualized_min_usd=120000,
        annualized_max_usd=160000,
        original_salary_text="$60 - $80 / hr",
        category="API Development",
        tags=["golang", "rest api"],
        description_raw="<p>Immediate urgent contract for Go API engineer in EMEA.</p>",
        description_text="Immediate urgent contract for Go API engineer in EMEA.",
        content_hash="hash-222",
        canonical_fingerprint="fingerprint-222",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )

    job_invalid_url = NormalizedJob(
        id="job-333",
        source_name="weworkremotely",
        external_id="ext-3",
        url="",  # Missing/invalid URL
        title="Backend Software Developer",
        company_name="NoUrl Inc",
        is_remote=True,
        location_requirement="Nigeria",
        employment_type=EmploymentType.FULL_TIME,
        category="Engineering",
        tags=["python", "rest"],
        description_raw="<p>Backend software engineer located in Nigeria.</p>",
        description_text="Backend software engineer located in Nigeria.",
        content_hash="hash-333",
        canonical_fingerprint="fingerprint-333",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )

    temp_storage.save_normalized_job(job1)
    temp_storage.save_normalized_job(job2)
    temp_storage.save_normalized_job(job_invalid_url)
    return [job1, job2, job_invalid_url]


class TestDashboardServer:
    def test_dashboard_starts_and_serves_html(self, temp_storage):
        """Tests that dashboard server starts up and responds with HTML on root route."""
        server = DashboardServer(host="127.0.0.1", port=8599, db_path=temp_storage.db_path)
        server.start_background()

        try:
            url = "http://127.0.0.1:8599/"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                assert resp.status == 200
                html = resp.read().decode("utf-8")
                assert "Ann's Job Intelligence Dashboard" in html
                assert "APPLY FIRST" in html
                assert "FASTEST POTENTIAL CASH" in html
        finally:
            server.stop()

    def test_dashboard_handles_empty_database(self, temp_storage):
        """Tests that dashboard endpoints handle an empty database gracefully."""
        server = DashboardServer(host="127.0.0.1", port=8598, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # Summary API
            with urllib.request.urlopen("http://127.0.0.1:8598/api/summary") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assert data["total_jobs"] == 0
                assert data["nigeria_eligible"] == 0
                assert data["strong_matches"] == 0

            # Dashboard API
            with urllib.request.urlopen("http://127.0.0.1:8598/api/dashboard") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assert data["apply_first"] == []
                assert data["fastest_cash"] == []

            # Jobs List API
            with urllib.request.urlopen("http://127.0.0.1:8598/api/jobs") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assert data == []

        finally:
            server.stop()

    def test_dashboard_loads_and_ranks_jobs(self, temp_storage, sample_jobs):
        """Tests that database jobs are loaded, scored, ranked, and correctly served via API."""
        server = DashboardServer(host="127.0.0.1", port=8597, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # Summary API
            with urllib.request.urlopen("http://127.0.0.1:8597/api/summary") as resp:
                summary = json.loads(resp.read().decode("utf-8"))
                assert summary["total_jobs"] == 3
                assert summary["nigeria_eligible"] >= 2

            # Dashboard API
            with urllib.request.urlopen("http://127.0.0.1:8597/api/dashboard") as resp:
                dash = json.loads(resp.read().decode("utf-8"))
                assert "apply_first" in dash
                assert "fastest_cash" in dash
                assert "best_technical_match" in dash

            # Jobs List API
            with urllib.request.urlopen("http://127.0.0.1:8597/api/jobs") as resp:
                jobs = json.loads(resp.read().decode("utf-8"))
                assert len(jobs) == 3

        finally:
            server.stop()

    def test_dashboard_handles_missing_urls_and_single_job_lookup(self, temp_storage, sample_jobs):
        """Tests that missing job URLs are handled gracefully and single job endpoint works."""
        server = DashboardServer(host="127.0.0.1", port=8596, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # Lookup job-111 (valid URL)
            with urllib.request.urlopen("http://127.0.0.1:8596/api/jobs/job-111") as resp:
                rec = json.loads(resp.read().decode("utf-8"))
                assert rec["job"]["id"] == "job-111"
                assert rec["job"]["url"] == "https://remotive.com/job/111"
                assert rec["explanation"]["priority_score"] > 0

            # Lookup job-333 (empty URL)
            with urllib.request.urlopen("http://127.0.0.1:8596/api/jobs/job-333") as resp:
                rec = json.loads(resp.read().decode("utf-8"))
                assert rec["job"]["id"] == "job-333"
                assert rec["job"]["url"] == ""

            # Lookup non-existent job ID -> 404
            req = urllib.request.Request("http://127.0.0.1:8596/api/jobs/non-existent-999")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 404

        finally:
            server.stop()

    def test_reports_latest_endpoint(self, temp_storage):
        """Tests that latest report API endpoint responds with valid Markdown string."""
        server = DashboardServer(host="127.0.0.1", port=8595, db_path=temp_storage.db_path)
        server.start_background()

        try:
            with urllib.request.urlopen("http://127.0.0.1:8595/api/reports/latest") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assert "content" in data
                assert "ANN'S DAILY REMOTE JOB INTELLIGENCE" in data["content"]
        finally:
            server.stop()

    def test_review_state_mutation_and_persistence(self, temp_storage, sample_jobs):
        """Tests updating review_state (UNREVIEWED -> REVIEWING -> DISMISSED) and persisting in SQLite."""
        server = DashboardServer(host="127.0.0.1", port=8594, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # Initial state: UNREVIEWED
            j1 = temp_storage.get_job_by_id("job-111")
            assert j1.review_state == "UNREVIEWED"

            # Update review_state to REVIEWING via POST
            body = json.dumps({"review_state": "REVIEWING"}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:8594/api/jobs/job-111/review_state",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                assert res["success"] is True
                assert res["review_state"] == "REVIEWING"

            j1_updated = temp_storage.get_job_by_id("job-111")
            assert j1_updated.review_state == "REVIEWING"

            # Update review_state to DISMISSED via POST
            body = json.dumps({"review_state": "DISMISSED"}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:8594/api/jobs/job-111/review_state",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                assert res["success"] is True

            j1_dismissed = temp_storage.get_job_by_id("job-111")
            assert j1_dismissed.review_state == "DISMISSED"

        finally:
            server.stop()

    def test_mark_as_applied_intent(self, temp_storage, sample_jobs):
        """Tests explicit mark_as_applied intent API recording applied_at in SQLite."""
        server = DashboardServer(host="127.0.0.1", port=8593, db_path=temp_storage.db_path)
        server.start_background()

        try:
            # Initial state: applied_at is None
            j2 = temp_storage.get_job_by_id("job-222")
            assert j2.applied_at is None

            # Mark as applied intent via POST
            body = json.dumps({"applied": True}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:8593/api/jobs/job-222/apply_intent",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                assert res["success"] is True
                assert res["applied_at"] is not None

            j2_applied = temp_storage.get_job_by_id("job-222")
            assert j2_applied.applied_at is not None

        finally:
            server.stop()
