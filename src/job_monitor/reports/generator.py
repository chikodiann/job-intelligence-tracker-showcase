from datetime import datetime, timezone
from typing import Dict, List, Optional
from ..scoring.ranking import JobQueryService, ScoredJobRecord
from ..scoring.relevance import RoleRelevance
from ..scoring.eligibility import RemoteEligibility
from ..utils.logging import setup_logger

logger = setup_logger("reports.generator")


class DailyReportGenerator:
    """Generates human-readable markdown daily job intelligence reports for Ann."""

    def __init__(self, query_service: JobQueryService):
        self.query_service = query_service

    def generate_report(self, date_str: Optional[str] = None) -> str:
        """Generates complete daily job intelligence report in specified 8-section layout."""
        now = datetime.now(timezone.utc)
        today = date_str or now.strftime("%Y-%m-%d")

        # Fetch Ranked Views
        apply_first = self.query_service.get_apply_first_jobs(limit=5)
        fast_cash = self.query_service.get_fastest_cash_jobs(limit=5)
        tech_matches = self.query_service.get_best_technical_matches(limit=5)
        long_term = self.query_service.get_best_long_term_jobs(limit=5)
        unclear_elig = self.query_service.get_unclear_eligibility_jobs(limit=5)

        # AI & Secondary Skill Filter
        all_scored = self.query_service.evaluate_and_persist_matches()
        ai_evals = [
            r for r in all_scored
            if "AI_TECHNICAL_EVALUATION" in r.explanation.classifications
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
        ][:5]
        secondary_skills = [
            r for r in all_scored
            if "SECONDARY_SKILL" in r.explanation.classifications
            and r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
        ][:5]

        # Helper for tz-aware datetime difference
        def _diff_seconds(dt1: Optional[datetime], dt2: Optional[datetime]) -> float:
            if not dt1 or not dt2:
                return 0.0
            if dt1.tzinfo is None:
                dt1 = dt1.replace(tzinfo=timezone.utc)
            if dt2.tzinfo is None:
                dt2 = dt2.replace(tzinfo=timezone.utc)
            return (dt1 - dt2).total_seconds()

        # Genuinely NEW jobs (first seen == last seen or first_seen_at within 5 min)
        new_jobs = [
            r for r in all_scored
            if r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and r.explanation.remote_eligibility != RemoteEligibility.INELIGIBLE
            and abs(_diff_seconds(r.job.last_seen_at, r.job.first_seen_at)) < 300
        ][:5]

        # UPDATED jobs (last_seen_at > first_seen_at)
        updated_jobs = [
            r for r in all_scored
            if r.explanation.role_relevance != RoleRelevance.NON_TARGET_ROLE
            and _diff_seconds(r.job.last_seen_at, r.job.first_seen_at) >= 300
        ]

        # UNCHANGED jobs (fetched multiple times without field changes)
        unchanged_jobs = [r for r in all_scored if r.job.status == "ACTIVE" and _diff_seconds(r.job.last_seen_at, r.job.first_seen_at) >= 300]

        # CLOSED / REMOVED jobs
        closed_jobs = [r for r in all_scored if r.job.status == "CLOSED"]

        # Executive Summary metrics
        total_new = len(new_jobs)
        total_updated = len(updated_jobs)
        total_unchanged = len(unchanged_jobs)
        total_closed = len(closed_jobs)
        total_fast_cash = len(fast_cash)
        total_long_term = len(long_term)

        lines = [
            "=" * 60,
            "ANN'S DAILY REMOTE JOB INTELLIGENCE",
            f"Date: {today}",
            "=" * 60,
            "\nEXECUTIVE SUMMARY",
            f"  - New Relevant Opportunities:       {total_new}",
            f"  - Updated Relevant Opportunities:   {total_updated}",
            f"  - Unchanged Relevant Opportunities: {total_unchanged}",
            f"  - Closed/Removed Opportunities:     {total_closed}",
            f"  - Top Immediate-Cash Opportunities: {total_fast_cash}",
            f"  - Top Long-Term Career Roles:       {total_long_term}",
            f"  - Total Evaluated Positions:          {len(all_scored)}",
            "\n" + "-" * 60,
        ]

        # Section A: APPLY FIRST
        lines.append("\n1. APPLY FIRST")
        lines.append("Highest-priority eligible TARGET_ROLE opportunities to apply for immediately.\n")
        lines.extend(self._format_section_records(apply_first))

        # Section B: FASTEST POTENTIAL CASH
        lines.append("\n2. FASTEST POTENTIAL CASH")
        lines.append("Short-term contracts, hourly, and fast hiring path opportunities with strong technical fit.\n")
        lines.extend(self._format_section_records(fast_cash))

        # Section C: BEST TECHNICAL MATCH
        lines.append("\n3. BEST TECHNICAL MATCH")
        lines.append("Strongest engineering alignment with Ann's Java, Spring Boot, REST API, & PostgreSQL background.\n")
        lines.extend(self._format_section_records(tech_matches))

        # Section D: BEST LONG-TERM CAREER
        lines.append("\n4. BEST LONG-TERM CAREER")
        lines.append("Full-time/permanent engineering roles with strong career alignment.\n")
        lines.extend(self._format_section_records(long_term))

        # Section E: AI / TECHNICAL EVALUATION
        lines.append("\n5. AI / TECHNICAL EVALUATION")
        lines.append("AI coding evaluation, LLM training, and technical code review roles.\n")
        lines.extend(self._format_section_records(ai_evals))

        # Section F: SECONDARY SKILL OPPORTUNITIES
        lines.append("\n6. SECONDARY SKILL OPPORTUNITIES")
        lines.append("Technical PM, Technical BA, and API Documentation roles.\n")
        lines.extend(self._format_section_records(secondary_skills))

        # Section G: NEW RELEVANT OPPORTUNITIES
        lines.append("\n7. NEW RELEVANT OPPORTUNITIES")
        lines.append("Genuinely newly discovered relevant opportunities.\n")
        lines.extend(self._format_section_records(new_jobs))

        # Section H: IMPORTANT UPDATES & ELIGIBILITY UNCLEAR
        lines.append("\n8. IMPORTANT UPDATES & ELIGIBILITY UNCLEAR")
        lines.append("Opportunities with unclear geographic eligibility or state updates.\n")
        lines.extend(self._format_section_records(unclear_elig))

        lines.append("=" * 60)
        lines.append("END OF REPORT")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _format_section_records(self, records: List[ScoredJobRecord]) -> List[str]:
        if not records:
            return ["  * No opportunities matched this category today.\n"]

        formatted = []
        for idx, rec in enumerate(records, 1):
            j = rec.job
            e = rec.explanation
            class_str = " / ".join(e.classifications[:2]) if e.classifications else "STANDARD"

            if e.remote_eligibility == RemoteEligibility.UNKNOWN:
                remote_str = "UNKNOWN (Geographic eligibility could not be confirmed.)"
            else:
                remote_str = f"{e.remote_eligibility.value} ({j.location_requirement or 'Worldwide'})"

            formatted.extend([
                f"#{idx} {j.title} — {j.company_name}",
                f"    Role:           {e.role_relevance.value}",
                f"    Remote:         {remote_str}",
                f"    Compensation:   {e.compensation_text}",
                f"    Tech Match:     {e.technical_match_score}/100",
                f"    Priority Score: {e.priority_score}/100",
                f"    Classification: {class_str}",
                f"    WHY:            {e.why_match}",
                f"    POTENTIAL GAP:  {e.potential_gap}",
                f"    APPLICATION:    {j.url or 'Direct link unavailable'}",
                "",
            ])
        return formatted

