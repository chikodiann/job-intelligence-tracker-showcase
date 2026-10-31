import time
from typing import List, Optional
from job_monitor.interfaces import BaseJobFetcher
from job_monitor.models import RawJob


class MockFetcher(BaseJobFetcher):
    def __init__(self):
        super().__init__(source_name="mock_source", rate_limit_delay_seconds=0.2)

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        self.enforce_rate_limit()
        return [
            RawJob(
                source_name=self.source_name,
                external_id="1",
                payload={"title": "Mock Job"}
            )
        ]


def test_rate_limit_enforcer():
    fetcher = MockFetcher()
    t0 = time.time()
    fetcher.fetch_jobs()
    t1 = time.time()
    fetcher.fetch_jobs()
    t2 = time.time()

    first_call_duration = t1 - t0
    second_call_duration = t2 - t1

    assert first_call_duration < 0.1
    assert second_call_duration >= 0.18  # Rate limit of 0.2s enforced
