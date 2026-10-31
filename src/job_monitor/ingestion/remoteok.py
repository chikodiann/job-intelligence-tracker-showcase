import json
import urllib.request
from typing import List, Optional
from ..interfaces.fetcher import BaseJobFetcher
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger

logger = setup_logger("ingestion.remoteok")


class RemoteOKFetcher(BaseJobFetcher):
    """Concrete fetcher for RemoteOK API (https://remoteok.com/api)."""

    def __init__(
        self,
        endpoint_url: str = "https://remoteok.com/api",
        rate_limit_delay_seconds: float = 2.0,
        user_agent: str = "RemoteJobCashflowMonitor/1.0",
        request_timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name="remoteok",
            rate_limit_delay_seconds=rate_limit_delay_seconds,
            user_agent=user_agent,
        )
        self.endpoint_url = endpoint_url
        self.request_timeout_seconds = request_timeout_seconds

    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        """Fetches remote jobs from RemoteOK public JSON API."""
        self.enforce_rate_limit()

        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        req = urllib.request.Request(self.endpoint_url, headers=headers)

        logger.info("Fetching jobs from RemoteOK API: %s", self.endpoint_url)
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                if response.status != 200:
                    logger.error("RemoteOK HTTP error status %d", response.status)
                    return []

                body = response.read().decode("utf-8")
                data = json.loads(body)

                if not isinstance(data, list):
                    logger.error("RemoteOK payload is not a list")
                    return []

                raw_jobs: List[RawJob] = []
                for item in data:
                    if not isinstance(item, dict):
                        continue

                    # RemoteOK includes legal header as element 0 without an 'id'
                    ext_id = str(item.get("id") or "").strip()
                    if not ext_id:
                        continue

                    raw_jobs.append(
                        RawJob(
                            source_name=self.source_name,
                            external_id=ext_id,
                            payload=item,
                        )
                    )

                logger.info("Retrieved %d jobs from RemoteOK API", len(raw_jobs))

                if limit and len(raw_jobs) > limit:
                    raw_jobs = raw_jobs[:limit]

                return raw_jobs

        except Exception as e:
            logger.error("Failed to fetch jobs from RemoteOK API: %s", str(e))
            return []
