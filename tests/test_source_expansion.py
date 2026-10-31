import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json

from job_monitor.db.storage import JobStorage
from job_monitor.ingestion import (
    IngestionPipeline,
    RemoteOKFetcher,
    ArbeitnowFetcher,
    HimalayasFetcher,
    CryptoJobsFetcher,
    WWRFullstackFetcher,
    WWRDevOpsFetcher,
    JobNormalizer,
    JobDeduplicator,
)
from job_monitor.models import RawJob, NormalizedJob, EmploymentType, SalaryPeriod
from job_monitor.scoring.classifier import JobClassifier, JobCategoryTag
from job_monitor.scoring.relevance import RoleRelevanceClassifier, RoleRelevance
from job_monitor.scoring.eligibility import EligibilityClassifier, RemoteEligibility


# =====================================================================
# 1. REMOTE OK FETCHER & NORMALIZATION TESTS
# =====================================================================

def test_remoteok_fetcher_success():
    fetcher = RemoteOKFetcher(rate_limit_delay_seconds=0.0)
    mock_payload = [
        {"legal": "Notice"},  # Legal notice banner item (no ID)
        {
            "id": "rok-101",
            "position": "AI Coding Evaluator",
            "company": "Scale AI",
            "apply_url": "https://scale.com/careers/rok-101",
            "location": "Worldwide",
            "salary_min": 60000,
            "salary_max": 90000,
            "tags": ["python", "ai", "evaluator"],
            "description": "<p>Evaluate LLM generated Python code snippets.</p>",
            "date": "2026-10-06T12:00:00+00:00"
        }
    ]

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        raw_jobs = fetcher.fetch_jobs()
        assert len(raw_jobs) == 1
        assert raw_jobs[0].external_id == "rok-101"
        assert raw_jobs[0].source_name == "remoteok"


def test_remoteok_normalization():
    normalizer = JobNormalizer()
    raw_job = RawJob(
        source_name="remoteok",
        external_id="rok-101",
        payload={
            "id": "rok-101",
            "position": "AI Coding Evaluator",
            "company": "Scale AI",
            "apply_url": "https://scale.com/careers/rok-101",
            "location": "Worldwide",
            "salary_min": 60000,
            "salary_max": 90000,
            "tags": ["python", "ai"],
            "description": "<p>Evaluate Python code.</p>",
            "date": "2026-10-06T12:00:00+00:00"
        }
    )

    job = normalizer.normalize(raw_job)
    assert job is not None
    assert job.title == "AI Coding Evaluator"
    assert job.company_name == "Scale AI"
    assert job.url == "https://scale.com/careers/rok-101"
    assert job.salary_min == 60000.0
    assert job.salary_max == 90000.0
    assert job.location_requirement == "Worldwide"
    assert job.posted_at is not None


# =====================================================================
# 2. ARBEITNOW FETCHER & NORMALIZATION TESTS
# =====================================================================

def test_arbeitnow_fetcher_success():
    fetcher = ArbeitnowFetcher(rate_limit_delay_seconds=0.0)
    mock_payload = {
        "data": [
            {
                "slug": "backend-engineer-berlin-123",
                "title": "Backend Spring Boot Engineer",
                "company_name": "Tech Corp",
                "remote": True,
                "url": "https://www.arbeitnow.com/jobs/tech-corp/backend-engineer",
                "tags": ["Java", "Spring Boot", "PostgreSQL"],
                "job_types": ["Full Time"],
                "location": "Remote",
                "created_at": 1791394814,
                "description": "<p>Build microservices using Java and Spring Boot.</p>"
            }
        ]
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        raw_jobs = fetcher.fetch_jobs()
        assert len(raw_jobs) == 1
        assert raw_jobs[0].external_id == "backend-engineer-berlin-123"
        assert raw_jobs[0].source_name == "arbeitnow"


def test_arbeitnow_normalization():
    normalizer = JobNormalizer()
    raw_job = RawJob(
        source_name="arbeitnow",
        external_id="arbeitnow-1",
        payload={
            "slug": "arbeitnow-1",
            "title": "Senior Java Developer",
            "company_name": "EuroTech",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/eurotech/java-dev",
            "tags": ["Java", "Microservices"],
            "job_types": ["Contract"],
            "location": "Remote - Worldwide",
            "created_at": 1791394814,
            "description": "<p>Long-term Java microservices contract.</p>"
        }
    )

    job = normalizer.normalize(raw_job)
    assert job is not None
    assert job.title == "Senior Java Developer"
    assert job.company_name == "EuroTech"
    assert job.employment_type == EmploymentType.CONTRACT
    assert job.location_requirement == "Worldwide"
    assert job.posted_at is not None


# =====================================================================
# 3. HIMALAYAS & CRYPTOJOBS RSS TESTS
# =====================================================================

def test_himalayas_fetcher_and_normalization():
    fetcher = HimalayasFetcher(rate_limit_delay_seconds=0.0)
    normalizer = JobNormalizer()

    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>DataAnnotate Inc: Technical Data Annotator &amp; Reviewer</title>
                <link>https://himalayas.app/jobs/data-annotator-1</link>
                <guid>https://himalayas.app/jobs/data-annotator-1</guid>
                <pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate>
                <category>AI-Data</category>
                <description><![CDATA[Annotate and evaluate technical datasets. $40 per hour.]]></description>
            </item>
        </channel>
    </rss>
    """

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = xml_data.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        raw_jobs = fetcher.fetch_jobs()
        assert len(raw_jobs) == 1

        job = normalizer.normalize(raw_jobs[0])
        assert job is not None
        assert job.title == "Technical Data Annotator & Reviewer"
        assert job.company_name == "DataAnnotate Inc"
        assert job.salary_min == 40.0
        assert job.salary_period == SalaryPeriod.HOURLY


def test_cryptojobs_fetcher_and_normalization():
    fetcher = CryptoJobsFetcher(rate_limit_delay_seconds=0.0)
    normalizer = JobNormalizer()

    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Smart Contract Auditor at Web3 Security</title>
                <link>https://cryptojobslist.com/jobs/auditor-1</link>
                <guid>https://cryptojobslist.com/jobs/auditor-1</guid>
                <pubDate>Tue, 06 Oct 2026 18:00:00 GMT</pubDate>
                <description><![CDATA[Audit solidity and backend API code.]]></description>
            </item>
        </channel>
    </rss>
    """

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = xml_data.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        raw_jobs = fetcher.fetch_jobs()
        assert len(raw_jobs) == 1

        job = normalizer.normalize(raw_jobs[0])
        assert job is not None
        assert job.title == "Smart Contract Auditor"
        assert job.company_name == "Web3 Security"


# =====================================================================
# 4. FAST-CASH & AI EVALUATION CLASSIFICATION TESTS
# =====================================================================

@pytest.mark.parametrize("title, desc, emp_type, expected_fast_cash", [
    ("AI Response Evaluator", "Evaluate LLM answers", EmploymentType.UNKNOWN, True),
    ("Technical Data Annotator", "Annotate code snippets", EmploymentType.CONTRACT, True),
    ("Freelance API Developer", "Short term contract for REST API", EmploymentType.CONTRACT, True),
    ("Short-Term Technical Writer", "Write API documentation", EmploymentType.CONTRACT, True),
    ("Senior Java Backend Engineer", "Full time enterprise platform engineering", EmploymentType.FULL_TIME, False),
])
def test_fast_cash_classification(title, desc, emp_type, expected_fast_cash):
    job = NormalizedJob(
        source_name="test",
        external_id="test-1",
        url="https://example.com/job",
        title=title,
        company_name="Acme",
        location_requirement="Worldwide",
        employment_type=emp_type,
        description_text=desc
    )

    relevance, _ = RoleRelevanceClassifier.classify_relevance(job)
    assert relevance != RoleRelevance.NON_TARGET_ROLE

    tags = JobClassifier.classify(job, relevance)
    if expected_fast_cash:
        assert JobCategoryTag.FAST_CASH in tags
    else:
        assert JobCategoryTag.STABLE_CAREER in tags


# =====================================================================
# 5. CROSS-SOURCE DEDUPLICATION TESTS
# =====================================================================

def test_cross_source_deduplication():
    storage = JobStorage(db_path=":memory:")
    deduplicator = JobDeduplicator(storage=storage)

    job1 = NormalizedJob(
        source_name="remoteok",
        external_id="rok-999",
        url="https://company.com/apply/backend-dev",
        title="Backend Software Engineer",
        company_name="Global Tech",
        location_requirement="Worldwide",
        description_text="Python and PostgreSQL API development."
    )

    storage.save_normalized_job(job1)

    # Same job coming from Arbeitnow with same URL
    job2 = NormalizedJob(
        source_name="arbeitnow",
        external_id="arbeitnow-888",
        url="https://company.com/apply/backend-dev",  # Same canonical application URL
        title="Backend Software Engineer",
        company_name="Global Tech",
        location_requirement="Worldwide",
        description_text="Python and PostgreSQL API development."
    )

    res = deduplicator.check_duplicate(job2)
    assert res.is_duplicate is True
    assert res.match_level in ("URL", "FINGERPRINT", "CONTENT_HASH")


# =====================================================================
# 6. SOURCE FAILURE ISOLATION & METRICS TESTS
# =====================================================================

class FailingFetcher(RemoteOKFetcher):
    def fetch_jobs(self, limit=None):
        raise Exception("Source endpoint connection timed out!")


class WorkingFetcher(ArbeitnowFetcher):
    def __init__(self):
        super().__init__(rate_limit_delay_seconds=0.0)

    def fetch_jobs(self, limit=None):
        return [
            RawJob(
                source_name="arbeitnow",
                external_id="work-1",
                payload={
                    "slug": "work-1",
                    "title": "Software Engineer",
                    "company_name": "Good Co",
                    "url": "https://example.com/work-1",
                    "remote": True,
                    "description": "Python backend software engineer"
                }
            )
        ]


def test_pipeline_source_failure_isolation():
    storage = JobStorage(db_path=":memory:")
    pipeline = IngestionPipeline(
        storage=storage,
        fetchers=[FailingFetcher(), WorkingFetcher()]
    )

    # Execution must not crash despite FailingFetcher throwing Exception
    summary = pipeline.run()

    assert summary.total_fetched == 1
    assert summary.sources["remoteok"].failed == 1
    assert summary.sources["arbeitnow"].fetched == 1
    assert summary.sources["arbeitnow"].normalized == 1
    assert storage.count_jobs() == 1
