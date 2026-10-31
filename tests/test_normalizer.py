from datetime import datetime
from job_monitor.ingestion.normalizer import JobNormalizer
from job_monitor.models import RawJob, EmploymentType, SalaryPeriod


def test_normalize_remotive():
    raw = RawJob(
        source_name="remotive",
        external_id="101",
        payload={
            "id": 101,
            "url": "https://remotive.com/job/101",
            "title": "Senior Python Developer",
            "company_name": "DataCorp",
            "category": "Software Development",
            "tags": ["Python", "Django"],
            "job_type": "full_time",
            "publication_date": "2026-10-05T10:00:00Z",
            "candidate_required_location": "Worldwide",
            "salary": "$130k - $160k",
            "description": "<p>Great role!</p>"
        }
    )
    normalizer = JobNormalizer()
    job = normalizer.normalize(raw)

    assert job is not None
    assert job.source_name == "remotive"
    assert job.external_id == "101"
    assert job.title == "Senior Python Developer"
    assert job.company_name == "DataCorp"
    assert job.employment_type == EmploymentType.FULL_TIME
    assert job.salary_min == 130000.0
    assert job.salary_max == 160000.0
    assert job.salary_currency == "USD"
    assert job.description_text == "Great role!"
    assert job.canonical_fingerprint == "datacorp|seniorpythondeveloper|worldwide"


def test_normalize_jobicy():
    raw = RawJob(
        source_name="jobicy",
        external_id="jobicy-55",
        payload={
            "id": "jobicy-55",
            "url": "https://jobicy.com/jobs/55",
            "jobTitle": "Backend Engineer",
            "companyName": "CloudTech",
            "jobGeo": "USA Only",
            "jobType": "contract",
            "annualSalaryMin": "100000",
            "annualSalaryMax": "140000",
            "pubDate": "2026-10-06 14:00:00",
            "jobDescription": "<div>Write Python microservices</div>"
        }
    )
    normalizer = JobNormalizer()
    job = normalizer.normalize(raw)

    assert job is not None
    assert job.title == "Backend Engineer"
    assert job.company_name == "CloudTech"
    assert job.location_requirement == "USA Only"
    assert job.employment_type == EmploymentType.CONTRACT
    assert job.salary_min == 100000.0
    assert job.salary_max == 140000.0


def test_normalize_weworkremotely():
    raw = RawJob(
        source_name="weworkremotely",
        external_id="guid-wwr-123",
        payload={
            "title": "Acme Inc: Full Stack Engineer",
            "link": "https://weworkremotely.com/jobs/123",
            "guid": "guid-wwr-123",
            "pubDate": "Wed, 07 Oct 2026 08:00:00 +0000",
            "category": "Full Stack",
            "description": "<p>Salary: $80,000 - $110,000. Work on React and Node.</p>"
        }
    )
    normalizer = JobNormalizer()
    job = normalizer.normalize(raw)

    assert job is not None
    assert job.company_name == "Acme Inc"
    assert job.title == "Full Stack Engineer"
    assert job.salary_min == 80000.0
    assert job.salary_max == 110000.0
    assert job.category == "Full Stack"
