from abc import ABC, abstractmethod
from typing import Optional
from ..models.normalized_job import NormalizedJob
from ..models.raw_job import RawJob


class BaseNormalizer(ABC):
    """Abstract interface for job payload normalizers."""

    @abstractmethod
    def normalize(self, raw_job: RawJob) -> Optional[NormalizedJob]:
        """Parses a RawJob object into a canonical NormalizedJob model.
        
        Returns None if payload is corrupt or invalid.
        """
        pass
