from abc import ABC, abstractmethod
from typing import List, Tuple
from ..models.normalized_job import NormalizedJob


class BaseDeduplicator(ABC):
    """Abstract interface for job deduplication strategies."""

    @abstractmethod
    def generate_content_hash(self, job: NormalizedJob) -> str:
        """Generates SHA256 digest of normalized job core content."""
        pass

    @abstractmethod
    def generate_canonical_fingerprint(self, job: NormalizedJob) -> str:
        """Generates canonical string fingerprint (e.g. company + normalized title + remote type)."""
        pass

    @abstractmethod
    def deduplicate(self, jobs: List[NormalizedJob]) -> Tuple[List[NormalizedJob], List[NormalizedJob]]:
        """Deduplicates a batch of normalized jobs.
        
        Returns:
            Tuple of (unique_jobs, duplicate_jobs)
        """
        pass
