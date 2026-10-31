import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from ..db.storage import JobStorage
from ..models.normalized_job import NormalizedJob
from ..utils.logging import setup_logger
from .eligibility import RemoteEligibility
from .relevance import RoleRelevance
from .scorer import JobScorer, MatchExplanation

logger = setup_logger("scoring.ranking")


class ScoredJobRecord(BaseModel):
    """Container for normalized job coupled with its score & match explanation."""
    job: NormalizedJob
    explanation: MatchExplanation


class JobQueryService:
    """Service providing candidate ranking views and query APIs for Phase 4 consumption."""

    def __init__(self, storage: JobStorage, scorer: Optional[JobScorer] = None):
        self.storage = storage
        self.scorer = scorer or JobScorer()

    def evaluate_and_persist_matches(self, limit: int = 500) -> List[ScoredJobRecord]:
        """Evaluates stored jobs, computes scores & match explanations, and persists snapshots to job_matches."""
        jobs = self.storage.list_jobs(limit=limit)
        scored_records: List[ScoredJobRecord] = []

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            for job in jobs:
                explanation = self.scorer.evaluate_job(job)
                record = ScoredJobRecord(job=job, explanation=explanation)
                scored_records.append(record)

                # Persist snapshot into job_matches
                query = """
                INSERT INTO job_matches (
                    job_id, overall_score, keyword_score, cashflow_score, recency_score, match_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'NEW', CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    overall_score=excluded.overall_score,
                    keyword_score=excluded.keyword_score,
                    cashflow_score=excluded.cashflow_score,
                    recency_score=excluded.recency_score,
                    updated_at=CURRENT_TIMESTAMP
                """
                cursor.execute(
                    query,
                    (
                        job.id,
                        explanation.priority_score,
                        explanation.technical_match_score,
                        explanation.income_urgency_score,
                        explanation.freshness_factor * 100.0,
                    ),
                )
            conn.commit()

        return scored_records

    def _get_applied_job_ids(self) -> set:
        """Retrieves set of job_ids that already have application records or applied_at set."""
        apps = self.storage.list_applications()
        applied_ids = {app.job_id for app in apps}
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT id FROM jobs WHERE applied_at IS NOT NULL").fetchall()
            for r in rows:
                applied_ids.add(r["id"])
        return applied_ids

    def _is_active_recommendation(self, record: ScoredJobRecord, applied_ids: set) -> bool:
        """Check if a job is an active recommendation candidate (not dismissed, not applied)."""
        return (
            record.job.review_state != "DISMISSED"
            and record.job.applied_at is None
            and record.job.id not in applied_ids
        )

    def get_apply_first_jobs(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 1: APPLY_FIRST (Top TARGET_ROLE jobs with ELIGIBLE remote status ordered by Priority Score)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        valid = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and r.explanation.role_relevance == RoleRelevance.TARGET_ROLE
            and r.explanation.remote_eligibility == RemoteEligibility.ELIGIBLE
            and r.explanation.priority_score > 0.0
        ]
        valid.sort(key=lambda r: r.explanation.priority_score, reverse=True)
        return valid[:limit]

    def get_fastest_cash_jobs(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 2: FASTEST_CASH (Top ELIGIBLE TARGET/ADJACENT jobs tagged FAST_CASH with technical match >= 30.0)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        fast_cash = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and "FAST_CASH" in r.explanation.classifications
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility == RemoteEligibility.ELIGIBLE
            and r.explanation.technical_match_score >= 30.0
            and r.explanation.income_urgency_score > 0.0
        ]
        fast_cash.sort(key=lambda r: r.explanation.income_urgency_score, reverse=True)
        return fast_cash[:limit]

    def get_best_long_term_jobs(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 3: BEST_LONG_TERM (Top STABLE_CAREER jobs ordered by Priority Score, excluding INELIGIBLE)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        long_term = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and "STABLE_CAREER" in r.explanation.classifications
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
            and r.explanation.priority_score > 0.0
        ]
        long_term.sort(key=lambda r: r.explanation.priority_score, reverse=True)
        return long_term[:limit]

    def get_best_technical_matches(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 4: BEST_TECHNICAL_MATCH (Top TARGET/ADJACENT jobs ordered by Technical Match Score, excluding INELIGIBLE)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        valid = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
            and r.explanation.technical_match_score > 0.0
        ]
        valid.sort(key=lambda r: r.explanation.technical_match_score, reverse=True)
        return valid[:limit]

    def get_highest_compensation_jobs(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 5: HIGHEST_COMPENSATION (Top TARGET/ADJACENT jobs with known salary ordered by compensation value)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        with_salary = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and (r.job.salary_min or r.job.annualized_min_usd)
        ]
        with_salary.sort(
            key=lambda r: (r.job.annualized_min_usd or r.job.salary_min or 0.0),
            reverse=True,
        )
        return with_salary[:limit]

    def get_newest_high_matches(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 6: NEWEST_HIGH_MATCH (Jobs posted in last 72 hours with priority > 40 ordered by posted_at)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        recent = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.freshness_factor >= 0.70
            and r.explanation.priority_score >= 40.0
        ]
        recent.sort(
            key=lambda r: r.job.posted_at or datetime.min,
            reverse=True,
        )
        return recent[:limit]

    def get_unclear_eligibility_jobs(self, limit: int = 10) -> List[ScoredJobRecord]:
        """View 7: ELIGIBILITY_UNCLEAR (TARGET/ADJACENT jobs where remote_eligibility == UNKNOWN)."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        unclear = [
            r for r in all_scored
            if self._is_active_recommendation(r, applied_ids)
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility == RemoteEligibility.UNKNOWN
            and r.explanation.priority_score > 0.0
        ]
        unclear.sort(key=lambda r: r.explanation.priority_score, reverse=True)
        return unclear[:limit]

    def get_dashboard_recommendations(self, limit_per_section: int = 10) -> Dict[str, List[ScoredJobRecord]]:
        """Returns mutually exclusive active recommendation lists for the main dashboard sections."""
        applied_ids = self._get_applied_job_ids()
        all_scored = self.evaluate_and_persist_matches()
        active_scored = [r for r in all_scored if self._is_active_recommendation(r, applied_ids)]

        seen_ids: set = set()

        # 1. APPLY FIRST
        apply_first_candidates = [
            r for r in active_scored
            if r.explanation.role_relevance == RoleRelevance.TARGET_ROLE
            and r.explanation.remote_eligibility == RemoteEligibility.ELIGIBLE
            and r.explanation.priority_score > 0.0
        ]
        apply_first_candidates.sort(key=lambda r: r.explanation.priority_score, reverse=True)
        apply_first = apply_first_candidates[:limit_per_section]
        for r in apply_first:
            seen_ids.add(r.job.id)

        # 2. FASTEST CASH
        fast_cash_candidates = [
            r for r in active_scored
            if r.job.id not in seen_ids
            and "FAST_CASH" in r.explanation.classifications
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility == RemoteEligibility.ELIGIBLE
            and r.explanation.technical_match_score >= 30.0
            and r.explanation.income_urgency_score > 0.0
        ]
        fast_cash_candidates.sort(key=lambda r: r.explanation.income_urgency_score, reverse=True)
        fast_cash = fast_cash_candidates[:limit_per_section]
        for r in fast_cash:
            seen_ids.add(r.job.id)

        # 3. BEST TECHNICAL MATCH
        tech_match_candidates = [
            r for r in active_scored
            if r.job.id not in seen_ids
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
            and r.explanation.technical_match_score > 0.0
        ]
        tech_match_candidates.sort(key=lambda r: r.explanation.technical_match_score, reverse=True)
        tech_match = tech_match_candidates[:limit_per_section]
        for r in tech_match:
            seen_ids.add(r.job.id)

        # 4. BEST LONG-TERM CAREER
        long_term_candidates = [
            r for r in active_scored
            if r.job.id not in seen_ids
            and "STABLE_CAREER" in r.explanation.classifications
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
            and r.explanation.priority_score > 0.0
        ]
        long_term_candidates.sort(key=lambda r: r.explanation.priority_score, reverse=True)
        long_term = long_term_candidates[:limit_per_section]
        for r in long_term:
            seen_ids.add(r.job.id)

        # 5. NEW TODAY
        new_today_candidates = [
            r for r in active_scored
            if r.job.id not in seen_ids
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.freshness_factor >= 0.70
            and r.explanation.priority_score >= 40.0
        ]
        new_today_candidates.sort(key=lambda r: r.job.posted_at or datetime.min, reverse=True)
        new_today = new_today_candidates[:limit_per_section]
        for r in new_today:
            seen_ids.add(r.job.id)

        return {
            "apply_first": apply_first,
            "fastest_cash": fast_cash,
            "best_technical_match": tech_match,
            "best_long_term": long_term,
            "new_today": new_today,
        }

    def get_jobs_since(self, since_timestamp: datetime, limit: int = 100) -> List[ScoredJobRecord]:
        """Query API: Returns scored jobs created since a specified timestamp."""
        all_scored = self.evaluate_and_persist_matches(limit=limit)
        return [r for r in all_scored if r.job.first_seen_at >= since_timestamp]

    def get_updated_jobs_since(self, since_timestamp: datetime, limit: int = 100) -> List[ScoredJobRecord]:
        """Query API: Returns scored jobs updated since a specified timestamp."""
        all_scored = self.evaluate_and_persist_matches(limit=limit)
        return [r for r in all_scored if r.job.last_seen_at >= since_timestamp]

