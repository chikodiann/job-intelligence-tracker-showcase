import pytest
from datetime import datetime
from job_monitor.db.storage import JobStorage
from job_monitor.models import NormalizedJob, RawJob, EmploymentType, SalaryPeriod


@pytest.fixture
def in_memory_db():
    storage = JobStorage(db_path=":memory:")
    return storage


def test_init_db(in_memory_db: JobStorage):
    assert in_memory_db.count_jobs() == 0


def test_save_raw_payload(in_memory_db: JobStorage):
    raw = RawJob(
        source_name="remotive",
        external_id="ext-100",
        payload={"title": "DevOps Engineer", "company": "CloudInc"}
    )
    success = in_memory_db.save_raw_payload(raw)
    assert success is True


def test_save_and_get_normalized_job(in_memory_db: JobStorage):
    job = NormalizedJob(
        source_name="remotive",
        external_id="ext-200",
        url="https://remotive.com/job/200",
        title="Staff Engineer",
        company_name="Innovate Ltd",
        is_remote=True,
        employment_type=EmploymentType.FULL_TIME,
        salary_min=140000.0,
        salary_max=180000.0,
        salary_currency="USD",
        salary_period=SalaryPeriod.ANNUAL,
        annualized_min_usd=140000.0,
        annualized_max_usd=180000.0,
        category="Engineering",
        tags=["Python", "AWS", "Kubernetes"],
        description_raw="<p>Great job</p>",
        description_text="Great job",
        content_hash="hash_staff_eng",
        canonical_fingerprint="innovate ltd|staff engineer|remote",
        posted_at=datetime(2026, 10, 1, 12, 0, 0)
    )

    job_id, is_new = in_memory_db.save_normalized_job(job)
    assert job_id is not None
    assert is_new is True
    assert in_memory_db.count_jobs() == 1

    retrieved = in_memory_db.get_job_by_id(job_id)
    assert retrieved is not None
    assert retrieved.title == "Staff Engineer"
    assert retrieved.company_name == "Innovate Ltd"
    assert retrieved.salary_min == 140000.0
    assert retrieved.salary_max == 180000.0
    assert retrieved.tags == ["Python", "AWS", "Kubernetes"]
    assert retrieved.employment_type == EmploymentType.FULL_TIME
    assert retrieved.salary_period == SalaryPeriod.ANNUAL


def test_duplicate_fingerprint_check(in_memory_db: JobStorage):
    job = NormalizedJob(
        source_name="jobicy",
        external_id="ext-300",
        url="https://jobicy.com/300",
        title="Frontend Dev",
        company_name="UI Systems",
        content_hash="hash_frontend_99",
        canonical_fingerprint="ui systems|frontend dev|remote"
    )
    in_memory_db.save_normalized_job(job)

    assert in_memory_db.exists_by_fingerprint_or_hash("ui systems|frontend dev|remote", "different_hash") is True
    assert in_memory_db.exists_by_fingerprint_or_hash("other_fp", "hash_frontend_99") is True
    assert in_memory_db.exists_by_fingerprint_or_hash("nonexistent_fp", "nonexistent_hash") is False
