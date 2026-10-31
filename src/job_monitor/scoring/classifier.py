import re
from enum import Enum
from typing import List
from ..models.normalized_job import EmploymentType, NormalizedJob, SalaryPeriod
from .relevance import RoleRelevance, RoleRelevanceClassifier


class JobCategoryTag(str, Enum):
    FAST_CASH = "FAST_CASH"
    STABLE_CAREER = "STABLE_CAREER"
    HIGH_VALUE_CONTRACT = "HIGH_VALUE_CONTRACT"
    AI_TECHNICAL_EVALUATION = "AI_TECHNICAL_EVALUATION"
    SECONDARY_SKILL = "SECONDARY_SKILL"


class JobClassifier:
    """Classifies relevant jobs into dual objectives and functional categories."""

    AI_EVALUATION_PATTERNS = [
        r"\bai\s+coding\s+evaluator\b",
        r"\bai\s+code\s+reviewer\b",
        r"\bai\s+software\s+engineering\s+trainer\b",
        r"\bai\s+technical\s+evaluator\b",
        r"\bllm\s+code\s+evaluator\b",
        r"\bcoding\s+benchmark\s+evaluator\b",
        r"\btechnical\s+ai\s+trainer\b",
        r"\btechnical\s+data\s+annotator\b",
        r"\bsoftware\s+engineering\s+ai\s+evaluator\b",
        r"\bai\s+trainer\b",
        r"\bcode\s+trainer\b",
        r"\bai\s+evaluator\b",
        r"\bai\s+response\s+evaluator\b",
        r"\bai\s+model\s+evaluator\b",
        r"\bprompt\s+evaluator\b",
        r"\bllm\s+evaluator\b",
        r"\bsearch\s+evaluator\b",
        r"\bdata\s+annotator\b",
        r"\bdata\s+annotation\b",
        r"\bdata\s+labeling\b",
        r"\bdata\s+labeler\b",
        r"\bai\s+quality\s+reviewer\b",
        r"\bai\s+quality\s+analyst\b",
        r"\bcoding\s+evaluator\b",
        r"\bcode\s+evaluator\b",
        r"\btechnical\s+reviewer\b",
    ]

    SECONDARY_SKILL_PATTERNS = [
        r"\bbusiness\s+analyst\b",
        r"\btechnical\s+business\s+analyst\b",
        r"\bproject\s+manager\b",
        r"\btechnical\s+project\s+manager\b",
        r"\bproject\s+coordinator\b",
        r"\btechnical\s+project\s+coordinator\b",
        r"\bscrum\s+master\b",
        r"\bscrum\b",
        r"\btechnical\s+writer\b",
        r"\btechnical\s+writing\b",
        r"\bapi\s+documentation\b",
        r"\btechnical\s+documentation\b",
        r"\bproofread\w*\b",
        r"\beditor\b",
        r"\bresearcher?\b",
        r"\bai\s+operations\b",
        r"\bdata\s+operations\b",
    ]

    @classmethod
    def classify(cls, job: NormalizedJob, relevance: RoleRelevance) -> List[JobCategoryTag]:
        """Returns list of applicable classification tags for a job record."""
        # NON_TARGET_ROLE receives NO target classifications
        if relevance == RoleRelevance.NON_TARGET_ROLE:
            return []

        tags: List[JobCategoryTag] = []
        text = f"{job.title} {job.category or ''} {job.description_text[:500]}".lower()

        # 1. AI Technical Evaluation
        is_ai_eval = any(re.search(pat, text) for pat in cls.AI_EVALUATION_PATTERNS)
        if is_ai_eval:
            tags.append(JobCategoryTag.AI_TECHNICAL_EVALUATION)
            tags.append(JobCategoryTag.FAST_CASH)

        # 2. Secondary Skill
        is_secondary = any(re.search(pat, text) for pat in cls.SECONDARY_SKILL_PATTERNS)
        if is_secondary:
            tags.append(JobCategoryTag.SECONDARY_SKILL)

        # 3. Employment Type & Contract Classification
        is_contract = (
            job.employment_type in (EmploymentType.CONTRACT, EmploymentType.FRACTIONAL)
            or job.salary_period == SalaryPeriod.HOURLY
            or "contract" in text
            or "freelance" in text
            or "hourly" in text
        )

        if is_contract:
            if JobCategoryTag.FAST_CASH not in tags:
                tags.append(JobCategoryTag.FAST_CASH)

            # High Value Contract (Descriptive tag ONLY)
            is_high_val = False
            if job.salary_period == SalaryPeriod.HOURLY and job.salary_min and job.salary_min >= 30.0:
                is_high_val = True
            elif job.annualized_min_usd and job.annualized_min_usd >= 60000.0:
                is_high_val = True

            if is_high_val:
                tags.append(JobCategoryTag.HIGH_VALUE_CONTRACT)

        # 4. Stable Career (Full-time / Permanent)
        is_fulltime = (
            job.employment_type == EmploymentType.FULL_TIME
            or ("full-time" in text or "full time" in text or "permanent" in text)
        )
        if is_fulltime or (not is_contract and not is_ai_eval):
            tags.append(JobCategoryTag.STABLE_CAREER)

        if not tags:
            tags.append(JobCategoryTag.STABLE_CAREER)

        return list(set(tags))
