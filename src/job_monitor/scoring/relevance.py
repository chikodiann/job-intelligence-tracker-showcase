import re
from enum import Enum
from typing import Optional, Tuple
from ..models.normalized_job import NormalizedJob
from .candidate_profile import CandidateProfile, get_default_candidate_profile


class RoleRelevance(str, Enum):
    TARGET_ROLE = "TARGET_ROLE"
    ADJACENT_ROLE = "ADJACENT_ROLE"
    NON_TARGET_ROLE = "NON_TARGET_ROLE"


class RoleCategory(str, Enum):
    PRIMARY_BACKEND = "PRIMARY_BACKEND"
    BACKEND_HEAVY_FULLSTACK = "BACKEND_HEAVY_FULLSTACK"
    FRONTEND_FIRST = "FRONTEND_FIRST"
    TECHNICAL_OTHER = "TECHNICAL_OTHER"


class RoleRelevanceClassifier:
    """Classifies jobs into TARGET_ROLE, ADJACENT_ROLE, or NON_TARGET_ROLE based on title and candidate profile."""

    def __init__(self, candidate_profile: Optional[CandidateProfile] = None):
        self.candidate_profile = candidate_profile or get_default_candidate_profile()

    def classify(self, title: str, description: str = "") -> RoleRelevance:
        from ..models.normalized_job import NormalizedJob
        temp_job = NormalizedJob(
            source_name="temp",
            external_id="temp",
            url="https://example.com/temp",
            title=title,
            company_name="Company",
            description_text=description,
        )
        rel, _ = self.classify_relevance(temp_job, profile=self.candidate_profile)
        return rel

    def classify_job(self, job: NormalizedJob) -> Tuple[RoleRelevance, str]:
        return self.classify_relevance(job, profile=self.candidate_profile)

    NON_TARGET_TITLE_PATTERNS = [
        r"\bsales\b",
        r"\bsales\s+development\b",
        r"\bsdr\b",
        r"\baccount\s+executive\b",
        r"\brenewals?\s+manager\b",
        r"\bcustomer\s+success\b",
        r"\bmarketing\b",
        r"\brecruiter\b",
        r"\brecruiting\b",
        r"\bhospitality\b",
        r"\bnurse\b",
        r"\bnursing\b",
        r"\bhealthcare\b",
        r"\bphysician\b",
        r"\bclinical\b",
        r"\blegal\b",
        r"\baccounting\b",
        r"\baccountant\b",
        r"\bfinance\s+manager\b",
        r"\bfinancial\s+analyst\b",
        r"\badministrative\b",
        r"\bcustomer\s+service\b",
        r"\bcustomer\s+support\b",
        r"\bclient\s+experience\b",
        r"\bproducer\b",
        r"\bconstruction\b",
        r"\bcontent\s+writer\b",
        r"\bcopywriter\b",
        r"\bcommunity\s+manager\b",
        r"\bpeople\s+partner\b",
        r"\bhr\s+manager\b",
        r"\bhead\s+of\s+people\b",
    ]

    TARGET_TITLE_PATTERNS = [
        r"\bbackend\b",
        r"\bback-end\b",
        r"\bsoftware\s+engineer\b",
        r"\bsoftware\s+developer\b",
        r"\bjava\s+developer\b",
        r"\bjava\s+engineer\b",
        r"\bspring\s+boot\b",
        r"\bapi\s+engineer\b",
        r"\bapi\s+developer\b",
        r"\bintegration\s+engineer\b",
        r"\bmicroservices\s+engineer\b",
        r"\bplatform\s+engineer\b",
        r"\bdistributed\s+systems\b",
        r"\bfull\s+stack\s+engineer\b",
        r"\bfull-stack\s+engineer\b",
        r"\bfullstack\s+engineer\b",
        r"\bai\s+coding\b",
        r"\bai\s+code\b",
        r"\bcode\s+evaluator\b",
        r"\bcoding\s+evaluator\b",
        r"\bai\s+evaluator\b",
        r"\bai\s+trainer\b",
        r"\bai\s+response\s+evaluator\b",
        r"\bai\s+model\s+evaluator\b",
        r"\bprompt\s+evaluator\b",
        r"\bllm\s+evaluator\b",
        r"\bsearch\s+evaluator\b",
        r"\bdata\s+annotator\b",
        r"\bdata\s+annotation\b",
        r"\bdata\s+labeling\b",
        r"\bdata\s+labeler\b",
        r"\bai\s+quality\b",
        r"\btechnical\s+reviewer\b",
        r"\bcode\s+reviewer\b",
        r"\btechnical\s+ai\s+trainer\b",
        r"\bbusiness\s+analyst\b",
        r"\btechnical\s+business\s+analyst\b",
        r"\bproject\s+manager\b",
        r"\btechnical\s+project\s+manager\b",
        r"\bproject\s+coordinator\b",
        r"\btechnical\s+project\s+coordinator\b",
        r"\bscrum\s+master\b",
        r"\btechnical\s+writer\b",
        r"\btechnical\s+writing\b",
        r"\bapi\s+documentation\b",
        r"\btechnical\s+documentation\b",
        r"\bai\s+operations\b",
        r"\bdata\s+operations\b",
    ]

    TECHNICAL_EVIDENCE_PATTERNS = [
        r"\bjava\b",
        r"\bspring\s+boot\b",
        r"\bspring\s+security\b",
        r"\brest\s+api\b",
        r"\brestful\b",
        r"\bbackend\b",
        r"\bmicroservices\b",
        r"\bpostgresql\b",
        r"\bpostgres\b",
        r"\bsql\b",
        r"\bhibernate\b",
        r"\bjpa\b",
        r"\bsoftware\s+development\b",
        r"\bapi\s+integration\b",
        r"\bdistributed\s+systems\b",
        r"\bdocker\b",
        r"\baws\b",
        r"\bnode\.js\b",
        r"\bnodejs\b",
        r"\btypescript\b",
        r"\bpython\b",
        r"\bgolang\b",
        r"\bgo\s+backend\b",
        r"\btechnical\s+coding\b",
        r"\bcode\s+review\b",
        r"\bsoftware\s+architecture\b",
        r"\bfastapi\b",
        r"\bnestjs\b",
        r"\bexpress\.js\b",
        r"\bai\s+evaluation\b",
        r"\bdata\s+annotation\b",
        r"\bdata\s+labeling\b",
        r"\bprompt\s+engineering\b",
    ]

    FRONTEND_PATTERNS = [
        r"\bfrontend\b",
        r"\bfront-end\b",
        r"\breact\b",
        r"\bvue\b",
        r"\bangular\b",
        r"\bui\s+engineer\b",
        r"\bcss\b",
        r"\bshopify\b",
    ]

    @classmethod
    def classify_relevance(cls, job: NormalizedJob, profile: Optional[CandidateProfile] = None) -> Tuple[RoleRelevance, str]:
        prof = profile or get_default_candidate_profile()
        title = job.title.lower().strip()
        text = f"{title} {job.category or ''} {job.description_text[:1000]}".lower()

        # Build active target patterns from candidate profile
        target_patterns = list(prof.target_title_patterns) if prof.target_title_patterns else cls.TARGET_TITLE_PATTERNS
        for target_title in prof.target_titles:
            escaped = r"\b" + re.escape(target_title.lower().strip()) + r"\b"
            if escaped not in target_patterns:
                target_patterns.append(escaped)

        # Build active non-target patterns from candidate profile (excluding anything that is a target for this profile)
        non_target_patterns = []
        raw_non_target = prof.non_target_title_patterns if prof.non_target_title_patterns else cls.NON_TARGET_TITLE_PATTERNS
        for pat in raw_non_target:
            # Skip if pattern matches candidate's target titles
            if not any(re.search(pat, tt.lower()) for tt in prof.target_titles):
                non_target_patterns.append(pat)

        # 1. Check Explicit Non-Target Title Patterns
        for pat in non_target_patterns:
            if re.search(pat, title):
                if any(ex in title for ex in ("renewals", "hospitality", "nurse", "nursing", "clinical", "sdr", "account executive", "client experience", "producer")):
                    return RoleRelevance.NON_TARGET_ROLE, f"Non-target position title ('{title}')."
                if not cls.has_technical_evidence(text, prof):
                    return RoleRelevance.NON_TARGET_ROLE, f"Non-target title ('{title}') without profile skill evidence."

        # 2. Check Profile Technical Evidence
        has_tech_ev = cls.has_technical_evidence(text, prof)

        # 3. Check Explicit Target Title Patterns
        for pat in target_patterns:
            if re.search(pat, title):
                return RoleRelevance.TARGET_ROLE, f"Target role ('{title}')."

        # 4. Check if Description Has Strong Evidence
        if has_tech_ev:
            if any(term in title for term in ("engineer", "developer", "architect", "evaluator", "analyst", "assistant", "specialist", "manager", "coordinator")):
                return RoleRelevance.TARGET_ROLE, f"Role with strong profile skill evidence ('{title}')."
            else:
                return RoleRelevance.ADJACENT_ROLE, f"Position contains profile evidence but non-standard title ('{title}')."

        # 5. Default Fallback -> NON_TARGET_ROLE
        return RoleRelevance.NON_TARGET_ROLE, f"Role lacks candidate profile requirements or skill evidence."

    @classmethod
    def classify_role_category(cls, job: NormalizedJob, profile: Optional[CandidateProfile] = None) -> RoleCategory:
        """Determines whether role is PRIMARY_BACKEND, BACKEND_HEAVY_FULLSTACK, or FRONTEND_FIRST."""
        title = job.title.lower().strip()

        is_frontend = any(re.search(pat, title) for pat in cls.FRONTEND_PATTERNS)
        is_backend = any(term in title for term in ("backend", "java", "spring", "api", "microservices", "server"))

        if is_frontend and not is_backend:
            return RoleCategory.FRONTEND_FIRST
        elif "full stack" in title or "fullstack" in title or "full-stack" in title:
            return RoleCategory.BACKEND_HEAVY_FULLSTACK
        elif is_backend or any(term in title for term in ("software engineer", "developer", "platform", "architect")):
            return RoleCategory.PRIMARY_BACKEND
        return RoleCategory.TECHNICAL_OTHER

    @classmethod
    def has_technical_evidence(cls, text: str, profile: Optional[CandidateProfile] = None) -> bool:
        """Returns True if text contains candidate profile skill/evidence keywords."""
        prof = profile or get_default_candidate_profile()

        # Check candidate profile patterns
        patterns = prof.technical_evidence_patterns if prof.technical_evidence_patterns else cls.TECHNICAL_EVIDENCE_PATTERNS
        for pat in patterns:
            if re.search(pat, text):
                return True

        # Check candidate primary, additional, or secondary skills
        all_skills = prof.primary_skills.union(prof.additional_skills).union(prof.secondary_skills)
        for skill in all_skills:
            if skill.lower() in text:
                return True

        return False

