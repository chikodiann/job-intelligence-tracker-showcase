import json
import urllib.request
from typing import List, Optional
from ..interfaces.fetcher import BaseJobFetcher
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger

logger = setup_logger("ingestion.arbeitnow")


class ArbeitnowFetcher(BaseJobFetcher):
    """Concrete fetcher for Arbeitnow Public API (https://www.arbeitnow.com/api/job-board-api)."""

    def __init__(
        self,
        endpoint_url: str = "https://www.arbeitnow.com/api/job-board-api",
        rate_limit_delay_seconds: float = 2.0,
        user_agent: str = "RemoteJobCashflowMonitor/1.0",
        request_timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name="arbeitnow",
            rate_limit_delay_seconds=rate_limit_delay_seconds,
            user_agent=user_agent,
        )
        self.endpoint_url = endpoint_url
        self.request_timeout_seconds = request_timeout_seconds

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        """Fetches remote/engineering jobs from Arbeitnow JSON API."""
        self.enforce_rate_limit()

        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        req = urllib.request.Request(self.endpoint_url, headers=headers)

        logger.info("Fetching jobs from Arbeitnow API: %s", self.endpoint_url)
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                if response.status != 200:
                    logger.error("Arbeitnow HTTP error status %d", response.status)
                    return []

                body = response.read().decode("utf-8")
                data = json.loads(body)

                items = data.get("data", []) if isinstance(data, dict) else []
                raw_jobs: List[RawJob] = []

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    ext_id = str(item.get("slug") or item.get("id") or "").strip()
                    if not ext_id:
                        continue

                    raw_jobs.append(
                        RawJob(
                            source_name=self.source_name,
                            external_id=ext_id,
                            payload=item,
                        )
                    )

                logger.info("Retrieved %d jobs from Arbeitnow API", len(raw_jobs))

                if limit and len(raw_jobs) > limit:
                    raw_jobs = raw_jobs[:limit]

                return raw_jobs

        except Exception as e:
            logger.error("Failed to fetch jobs from Arbeitnow API: %s", str(e))
            return []
