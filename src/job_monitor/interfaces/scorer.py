from abc import ABC, abstractmethod
from typing import Dict
from ..models.cashflow import CashflowProfile
from ..models.normalized_job import NormalizedJob


class JobScoreResult:
    """Encapsulates composite scoring breakdown for candidate job."""
    def __init__(self, overall_score: float, keyword_score: float, cashflow_score: float, recency_score: float):
        self.overall_score = overall_score
        self.keyword_score = keyword_score
        self.cashflow_score = cashflow_score
        self.recency_score = recency_score


class BaseScorer(ABC):
    """Abstract interface for candidate matching, cashflow scoring, and ranking engine."""

    @abstractmethod
    def score_job(self, job: NormalizedJob, profile: CashflowProfile) -> JobScoreResult:
        """Calculates suitability score for a job posting against user cashflow profile."""
        pass
