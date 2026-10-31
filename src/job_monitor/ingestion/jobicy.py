import json
import urllib.request
from typing import Any, Dict, List, Optional
from ..interfaces.fetcher import BaseJobFetcher
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger

logger = setup_logger("ingestion.jobicy")


class JobicyFetcher(BaseJobFetcher):
    """Concrete fetcher for Jobicy API (https://jobicy.com/api/v2/remote-jobs)."""

    def __init__(
        self,
        endpoint_url: str = "https://jobicy.com/api/v2/remote-jobs",
        rate_limit_delay_seconds: float = 2.0,
        user_agent: str = "RemoteJobCashflowMonitor/1.0",
        request_timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name="jobicy",
            rate_limit_delay_seconds=rate_limit_delay_seconds,
            user_agent=user_agent,
        )
        self.endpoint_url = endpoint_url
        self.request_timeout_seconds = request_timeout_seconds

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        """Fetches remote jobs from Jobicy API."""
        self.enforce_rate_limit()

        url = self.endpoint_url
        if limit:
            url += f"?count={limit}"

        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)

        logger.info("Fetching jobs from Jobicy API: %s", url)
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                if response.status != 200:
                    logger.error("Jobicy HTTP error status %d", response.status)
                    return []

                body = response.read().decode("utf-8")
                data = json.loads(body)

                job_list = data.get("jobs", [])
                if not job_list and isinstance(data, list):
                    job_list = data

                logger.info("Retrieved %d jobs from Jobicy", len(job_list))

                raw_jobs = []
                for item in job_list:
                    # Jobicy uses id or jobSlug as unique identifier
                    ext_id = str(item.get("id") or item.get("jobSlug") or "")
                    if not ext_id:
                        continue

                    raw_jobs.append(
                        RawJob(
                            source_name=self.source_name,
                            external_id=ext_id,
                            payload=item,
                        )
                    )

                if limit and len(raw_jobs) > limit:
                    raw_jobs = raw_jobs[:limit]

                return raw_jobs

        except Exception as e:
            logger.error("Failed to fetch jobs from Jobicy API: %s", str(e))
            return []
