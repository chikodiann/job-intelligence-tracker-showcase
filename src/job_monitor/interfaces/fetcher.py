import time
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models.raw_job import RawJob
from ..utils.logging import setup_logger

logger = setup_logger("interfaces.fetcher")


class BaseJobFetcher(ABC):
    """Abstract interface for remote job source fetchers."""

    def __init__(self, source_name: str, rate_limit_delay_seconds: float = 2.0, user_agent: str = "RemoteJobCashflowMonitor/1.0"):
        self.source_name = source_name
        self.rate_limit_delay_seconds = rate_limit_delay_seconds
        self.user_agent = user_agent
        self.last_request_time: float = 0.0

    def enforce_rate_limit(self) -> None:
        """Enforces configured pause between HTTP requests to respect vendor rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay_seconds:
            sleep_duration = self.rate_limit_delay_seconds - elapsed
            logger.debug("Rate-limiting [%s]: sleeping for %.2fs", self.source_name, sleep_duration)
            time.sleep(sleep_duration)
        self.last_request_time = time.time()

    @abstractmethod
    def fetch_jobs(self, limit: Optional[int] = None) -> List[RawJob]:
        """Fetches raw job records from the remote source feed or API.
        
        Must handle network errors gracefully, enforce rate limiting via `enforce_rate_limit()`,
        and log failures clearly.
        """
        pass
