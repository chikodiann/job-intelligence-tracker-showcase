from typing import List, Optional
from job_monitor.db.storage import JobStorage
from job_monitor.ingestion import IngestionPipeline, RemotiveFetcher, JobicyFetcher, WWRRSSFetcher
from job_monitor.interfaces.fetcher import BaseJobFetcher
from job_monitor.models import RawJob


class MockRemotiveFetcher(BaseJobFetcher):
    def __init__(self):
        super().__init__(source_name="remotive", rate_limit_delay_seconds=0.0)

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        return [
            RawJob(
                source_name="remotive",
                external_id="remotive-1",
                payload={
                    "id": "remotive-1",
                    "title": "Backend Python Engineer",
                    "company_name": "Acme Software",
                    "url": "https://remotive.com/job/remotive-1",
                    "salary": "$120k - $150k",
                    "candidate_required_location": "Worldwide",
                    "description": "<p>Build Python microservices.</p>"
                }
            ),
            RawJob(
                source_name="remotive",
                external_id="remotive-2",
                payload={
                    "id": "remotive-2",
                    "title": "Junior QA Automation",
                    "company_name": "TestCo",
                    "url": "https://remotive.com/job/remotive-2",
                    "salary": "$25/hour",
                    "candidate_required_location": "Worldwide",
                    "description": "<p>Automate test suites.</p>"
                }
            )
        ]


class MockJobicyFetcher(BaseJobFetcher):
    def __init__(self):
        super().__init__(source_name="jobicy", rate_limit_delay_seconds=0.0)

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        return [
            # Duplicate job of remotive-1 (Same title & company)
            RawJob(
                source_name="jobicy",
                external_id="jobicy-100",
                payload={
                    "id": "jobicy-100",
                    "jobTitle": "Backend Python Engineer",
                    "companyName": "Acme Software",
                    "url": "https://remotive.com/job/remotive-1", # Duplicate URL
                    "jobGeo": "Worldwide",
                    "jobDescription": "Build Python microservices."
                }
            )
        ]


def test_ingestion_pipeline_end_to_end():
    storage = JobStorage(db_path=":memory:")
    pipeline = IngestionPipeline(
        storage=storage,
        fetchers=[MockRemotiveFetcher(), MockJobicyFetcher()]
    )

    # First Run
    summary1 = pipeline.run()

    assert summary1.total_fetched == 3
    assert summary1.total_new == 2
    assert summary1.total_duplicates == 1
    assert storage.count_jobs() == 2

    raw_payload = storage.get_raw_payload("remotive", "remotive-1")
    assert raw_payload is not None
    assert raw_payload["company_name"] == "Acme Software"

    # Second Run (Idempotency check)
    summary2 = pipeline.run()

    assert summary2.total_fetched == 3
    assert summary2.total_new == 0
    assert summary2.total_duplicates == 3
    assert storage.count_jobs() == 2  # No duplicate rows created!
