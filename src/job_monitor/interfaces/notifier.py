from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from ..models.normalized_job import NormalizedJob
from .scorer import JobScoreResult


class BaseNotifier(ABC):
    """Abstract interface for reporting and notification dispatchers."""

    @abstractmethod
    def send_digest(self, ranked_matches: List[Tuple[NormalizedJob, JobScoreResult]]) -> bool:
        """Sends summary report or desktop notification for top job matches."""
        pass

    def send_notification(self, title: str, message: str, subtitle: Optional[str] = None) -> bool:
        """Sends arbitrary alert notification across channel."""
        return True
