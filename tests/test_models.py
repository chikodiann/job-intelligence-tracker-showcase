from datetime import datetime
from job_monitor.models import NormalizedJob, RawJob, CashflowProfile, EmploymentType, SalaryPeriod


def test_raw_job_instantiation():
    raw = RawJob(
        source_name="remotive",
        external_id="12345",
        payload={"title": "Software Engineer"}
    )
    assert raw.source_name == "remotive"
    assert raw.external_id == "12345"
    assert raw.payload["title"] == "Software Engineer"
    assert isinstance(raw.fetched_at, datetime)


def test_normalized_job_defaults():
    job = NormalizedJob(
        source_name="jobicy",
        external_id="j-99",
        url="https://jobicy.com/jobs/99",
        title="Backend Developer",
        company_name="TechCorp",
        content_hash="abc123hash",
        canonical_fingerprint="techcorp|backend developer|remote"
    )
    assert job.source_name == "jobicy"
    assert job.is_remote is True
    assert job.employment_type == EmploymentType.UNKNOWN
    assert job.salary_period == SalaryPeriod.UNKNOWN
    assert job.tags == []


def test_cashflow_profile():
    profile = CashflowProfile(
        profile_name="Senior Remote Dev",
        target_annual_cashflow=120000.0,
        target_hourly_rate=75.0,
        desired_employment_types=[EmploymentType.FULL_TIME, EmploymentType.CONTRACT]
    )
    assert profile.target_annual_cashflow == 120000.0
    assert profile.target_hourly_rate == 75.0
    assert len(profile.desired_employment_types) == 2
