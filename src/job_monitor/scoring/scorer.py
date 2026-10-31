import re
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from ..interfaces.scorer import BaseScorer, JobScoreResult
from ..models.cashflow import CashflowProfile
from ..models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod
from ..utils.logging import setup_logger
from .candidate_profile import CandidateProfile, get_default_candidate_profile
from .classifier import JobClassifier
from .eligibility import EligibilityClassifier, RemoteEligibility
from .relevance import RoleCategory, RoleRelevance, RoleRelevanceClassifier

logger = setup_logger("scoring.scorer")


class MatchExplanation(BaseModel):
    """Detailed structured explanation of candidate matching & scoring rationale."""
    technical_match_score: float
    income_urgency_score: float
    priority_score: float
    freshness_factor: float
    role_relevance: RoleRelevance
    match_tier: str  # STRONG_MATCH, GOOD_MATCH, TRANSFERABLE, SKILL_GAP, NON_TARGET
    classifications: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    transferable_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    remote_eligibility: RemoteEligibility
    eligibility_reason: str
    compensation_text: str
    why_match: str
    potential_gap: str


class JobScorer(BaseScorer):
    """Concrete candidate matching, remote eligibility, role relevance, and scoring engine."""

    def __init__(self, candidate_profile: Optional[CandidateProfile] = None):
        self.profile = candidate_profile or get_default_candidate_profile()

    @property
    def candidate_profile(self) -> CandidateProfile:
        return self.profile

    def score_job(self, job: NormalizedJob, profile: Optional[CashflowProfile] = None) -> JobScoreResult:
        """Implements BaseScorer interface method returning composite JobScoreResult."""
        explanation = self.evaluate_job(job, profile)
        return JobScoreResult(
            overall_score=explanation.priority_score,
            keyword_score=explanation.technical_match_score,
            cashflow_score=explanation.income_urgency_score,
            recency_score=explanation.freshness_factor * 100.0,
        )

    def evaluate_job(self, job: NormalizedJob, profile: Optional[CashflowProfile] = None) -> MatchExplanation:
        """Calculates detailed scores, eligibility, classifications, and explanations based on candidate profile."""
        title_lower = job.title.lower().strip()
        text = f"{title_lower} {job.category or ''} {job.description_text}".lower()

        # 1. Role Relevance Gate
        relevance, relevance_reason = RoleRelevanceClassifier.classify_relevance(job, self.profile)

        # 2. Remote Eligibility Classification
        eligibility, elig_reason = EligibilityClassifier.classify(job.location_requirement, job.description_text)

        comp_text = job.original_salary_text or (f"${job.salary_min:,.0f} - ${job.salary_max:,.0f}" if job.salary_min and job.salary_max else "Undisclosed")

        # IF NON_TARGET_ROLE: ZERO OUT ALL SCORES AND RETURN NON_TARGET EXPLANATION
        if relevance == RoleRelevance.NON_TARGET_ROLE:
            return MatchExplanation(
                technical_match_score=0.0,
                income_urgency_score=0.0,
                priority_score=0.0,
                freshness_factor=0.40,
                role_relevance=RoleRelevance.NON_TARGET_ROLE,
                match_tier="NON_TARGET",
                classifications=[],
                matched_skills=[],
                transferable_skills=[],
                missing_skills=[],
                remote_eligibility=eligibility,
                eligibility_reason=elig_reason,
                compensation_text=comp_text,
                why_match=f"Non-target role for {self.profile.name}'s {self.profile.professional_title} background.",
                potential_gap=relevance_reason,
            )

        # IF INELIGIBLE: ZERO OUT ALL SCORES AND RETURN INELIGIBLE EXPLANATION
        if eligibility == RemoteEligibility.INELIGIBLE:
            return MatchExplanation(
                technical_match_score=0.0,
                income_urgency_score=0.0,
                priority_score=0.0,
                freshness_factor=self._calculate_freshness_factor(job.posted_at),
                role_relevance=relevance,
                match_tier="INELIGIBLE",
                classifications=[],
                matched_skills=[],
                transferable_skills=[],
                missing_skills=[],
                remote_eligibility=RemoteEligibility.INELIGIBLE,
                eligibility_reason=elig_reason,
                compensation_text=comp_text,
                why_match=f"Ineligible due to geographic restriction excluding {self.profile.location_country}-based candidates.",
                potential_gap=f"Geographic restriction excludes {self.profile.location_country}-based candidates.",
            )

        # 3. Skill Extraction & Matching for TARGET or ADJACENT Roles
        matched_primary = [s for s in self.profile.primary_skills if s.lower() in text]
        matched_additional = [s for s in self.profile.additional_skills if s.lower() in text]
        matched_transferable = [s for s in self.profile.transferable_skills if s.lower() in text]

        all_matched = list(dict.fromkeys(matched_primary + matched_additional))

        # Determine Match Tier
        if "java" in self.profile.primary_skills:
            if ("java" in text or "spring" in text or "spring boot" in text) and len(matched_primary) >= 1:
                match_tier = "STRONG_MATCH"
            elif "golang" in text or "go lang" in text or "go backend" in text or "python" in text or "fastapi" in text:
                match_tier = "TRANSFERABLE"
            elif len(matched_additional) >= 1 or "node" in text or "typescript" in text or "nestjs" in text:
                match_tier = "GOOD_MATCH"
            elif ("backend" in text or "api" in text or "microservices" in text) and len(matched_primary) >= 1:
                match_tier = "STRONG_MATCH"
            elif len(matched_transferable) >= 1:
                match_tier = "TRANSFERABLE"
            else:
                match_tier = "SKILL_GAP"
        else:
            # Profile-generic match tier determination
            if len(matched_primary) >= 2 or any(tt in title_lower for tt in self.profile.target_titles):
                match_tier = "STRONG_MATCH"
            elif len(matched_primary) >= 1 or len(matched_additional) >= 1:
                match_tier = "GOOD_MATCH"
            elif len(matched_transferable) >= 1:
                match_tier = "TRANSFERABLE"
            else:
                match_tier = "SKILL_GAP"

        # 4. Calculate Technical Match Score (0 - 100)
        # 30 pts: Stack alignment
        if "java" in self.profile.primary_skills:
            stack_pts = 8.0
            if "java" in text and ("spring" in text or "spring boot" in text):
                stack_pts = 30.0
            elif "java" in text or "spring" in text:
                stack_pts = 26.0
            elif "node" in text or "nestjs" in text or "typescript" in text or "express" in text:
                stack_pts = 21.0
            elif "python" in text or "golang" in text or "go backend" in text or "fastapi" in text:
                stack_pts = 17.0
            elif matched_primary:
                stack_pts = 15.0
        else:
            stack_pts = min(30.0, (len(matched_primary) * 12.0) + (len(matched_additional) * 5.0) + (len(matched_transferable) * 2.0))
            if stack_pts == 0.0 and (any(tt in title_lower for tt in self.profile.target_titles)):
                stack_pts = 15.0

        # 20 pts: Role alignment
        role_pts = 8.0
        if any(t in title_lower for t in self.profile.target_titles):
            role_pts = 20.0
        elif any(pat in title_lower for pat in self.profile.target_title_patterns):
            role_pts = 18.0
        elif any(t in title_lower for t in ("software engineer", "full stack", "platform", "developer", "specialist", "coordinator")):
            role_pts = 16.0
        elif any(t in title_lower for t in ("ai coding", "code evaluator", "ai trainer", "code reviewer")):
            role_pts = 14.0

        # 15 pts: Seniority / Experience alignment
        sen_pts = 15.0
        if "senior" in title_lower or "lead" in title_lower or "staff" in title_lower or "5+" in text or "6+" in text or "7+" in text:
            sen_pts = 15.0
        elif "mid" in title_lower or "3+" in text or "4+" in text:
            sen_pts = 13.0
        elif "junior" in title_lower or "intern" in title_lower:
            sen_pts = 7.0

        # 10 pts: Architecture / system / domain alignment
        arch_pts = 0.0
        if any(a in text for a in ("microservice", "microservices", "rest", "api", "postgresql", "sql", "aws", "docker", "kubernetes", "cloud", "virtual assistant")):
            arch_pts += 5.0
        if any(a in text for a in ("distributed", "kafka", "redis", "jpa", "hibernate", "integration", "automation")):
            arch_pts += 5.0

        # 10 pts: Domain alignment
        dom_pts = 7.0
        if any(d in text for d in self.profile.preferred_domains):
            dom_pts = 10.0
        elif any(d in text for d in ("saas", "enterprise", "healthtech", "edtech", "ai", "cloud")):
            dom_pts = 8.0

        # 10 pts: Remote eligibility
        elig_pts = 10.0 if eligibility == RemoteEligibility.ELIGIBLE else (4.0 if eligibility == RemoteEligibility.UNKNOWN else 0.0)

        # 5 pts: Compensation presence
        comp_pts = 5.0 if job.salary_min or job.original_salary_text else 3.0

        raw_tech_score = min(100.0, stack_pts + role_pts + sen_pts + arch_pts + dom_pts + elig_pts + comp_pts)

        # FRONTEND_FIRST PENALTY for Backend Profiles
        if "java" in self.profile.primary_skills:
            role_cat = RoleRelevanceClassifier.classify_role_category(job, self.profile)
            if role_cat == RoleCategory.FRONTEND_FIRST:
                raw_tech_score *= 0.70

        # 5. Calculate Freshness Factor
        freshness_factor = self._calculate_freshness_factor(job.posted_at)

        # 6. Calculate Income Urgency Score (0 - 100)
        speed_pts = 12.0
        if any(kw in text for kw in self.profile.fast_cash_keywords):
            speed_pts = 30.0
        elif job.employment_type in (EmploymentType.CONTRACT, EmploymentType.FRACTIONAL) or "contract" in text:
            speed_pts = 24.0

        comp_pts_urg = 15.0
        if "contract" in text or "evaluator" in text or "trainer" in text or "assistant" in text:
            comp_pts_urg = 25.0

        pay_struct_pts = 10.0
        if job.salary_period == SalaryPeriod.HOURLY or "hourly" in text or "contract" in text:
            pay_struct_pts = 20.0

        intl_pts = 15.0 if eligibility == RemoteEligibility.ELIGIBLE else (6.0 if eligibility == RemoteEligibility.UNKNOWN else 0.0)

        comp_val_pts = 5.0
        min_h = self.profile.minimum_hourly_usd or 40.0
        min_a = self.profile.minimum_salary_usd or 80000.0
        if job.salary_min and job.salary_min >= min_h and job.salary_period == SalaryPeriod.HOURLY:
            comp_val_pts = 10.0
        elif job.annualized_min_usd and job.annualized_min_usd >= min_a:
            comp_val_pts = 10.0

        raw_urgency_score = speed_pts + comp_pts_urg + pay_struct_pts + intl_pts + comp_val_pts

        # 7. Classifications
        classifications = [c.value for c in JobClassifier.classify(job, relevance)]

        # 8. Calculate Priority Score & Apply Role Relevance Caps
        comp_score_weight = 25.0
        if job.salary_period == SalaryPeriod.HOURLY and job.salary_min:
            comp_score_weight = min(50.0, (job.salary_min / max(1.0, min_h)) * 40.0)
        elif job.annualized_min_usd:
            comp_score_weight = min(50.0, (job.annualized_min_usd / max(1.0, min_a)) * 40.0)

        priority_score = (0.45 * raw_tech_score) + (0.35 * raw_urgency_score) + (0.20 * comp_score_weight)
        priority_score *= freshness_factor

        # Role Relevance Cap
        if relevance == RoleRelevance.ADJACENT_ROLE:
            priority_score = min(50.0, priority_score)

        # 9. Generate Why Match & Potential Gap Explanations
        why_match, potential_gap = self._generate_explanations(
            job, matched_primary, matched_additional, matched_transferable, match_tier, eligibility, relevance, raw_tech_score
        )

        return MatchExplanation(
            technical_match_score=round(raw_tech_score, 1),
            income_urgency_score=round(raw_urgency_score, 1),
            priority_score=round(priority_score, 1),
            freshness_factor=round(freshness_factor, 2),
            role_relevance=relevance,
            match_tier=match_tier,
            classifications=classifications,
            matched_skills=all_matched,
            transferable_skills=matched_transferable,
            missing_skills=[],
            remote_eligibility=eligibility,
            eligibility_reason=elig_reason,
            compensation_text=comp_text,
            why_match=why_match,
            potential_gap=potential_gap,
        )

    @staticmethod
    def _calculate_freshness_factor(posted_at: Optional[datetime]) -> float:
        if not posted_at:
            return 0.40

        now = datetime.now(timezone.utc)
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)

        age_hours = (now - posted_at).total_seconds() / 3600.0

        if age_hours <= 24:
            return 1.00
        elif age_hours <= 48:
            return 0.85
        elif age_hours <= 72:
            return 0.70
        else:
            return 0.50

    def _generate_explanations(
        self,
        job: NormalizedJob,
        matched_primary: List[str],
        matched_additional: List[str],
        matched_transferable: List[str],
        match_tier: str,
        eligibility: RemoteEligibility,
        relevance: RoleRelevance,
        tech_score: float,
    ) -> Tuple[str, str]:
        title_lower = job.title.lower()
        text_lower = job.description_text.lower()
        cand_name = self.profile.name

        # WHY MATCH: strictly driven by technical match score
        if tech_score >= 70.0:
            skills_str = ", ".join(s.title() for s in matched_primary[:3]) if matched_primary else f"{self.profile.professional_title} core skills"
            why = f"Strong {self.profile.professional_title} match. The role explicitly requires {skills_str}, which directly align with {cand_name}'s primary stack."
        elif tech_score >= 40.0:
            why = f"Moderate match for {cand_name}. The role overlaps with {self.profile.professional_title} responsibilities, but the primary stack differs slightly."
        else:
            why = f"Low technical match. The role does not substantially overlap with {cand_name}'s core background."

        # POTENTIAL GAP: driven by actual job requirements
        gaps = []
        if ("go" in text_lower or "golang" in text_lower) and not any(s in text_lower for s in ("java", "spring", "kubernetes", "aws", "assistant")):
            gaps.append(f"Primary gap: Go is not one of {cand_name}'s strongest production languages")
        elif ("terraform" in text_lower or "azure" in text_lower or "kubernetes" in text_lower) and "java" in self.profile.primary_skills and not ("java" in text_lower or "spring" in text_lower):
            gaps.append(f"Primary gap: cloud/IaC experience is adjacent to {cand_name}'s primary strength")
        elif any(fe in title_lower or fe in text_lower for fe in ("react", "angular", "vue", "frontend", "ui engineer")) and "java" in self.profile.primary_skills:
            gaps.append(f"Primary gap: this is frontend-heavy and does not closely match {cand_name}'s backend specialization")
        elif relevance == RoleRelevance.ADJACENT_ROLE:
            gaps.append(f"Primary gap: role is adjacent to primary {self.profile.professional_title} focus")
        elif eligibility == RemoteEligibility.UNKNOWN:
            gaps.append("Geographic eligibility is unconfirmed ('Remote' without country specifics)")

        if not gaps:
            potential_gap = "Potential gap: none obvious from the available job description."
        else:
            potential_gap = "; ".join(gaps) + "."

        return why, potential_gap


