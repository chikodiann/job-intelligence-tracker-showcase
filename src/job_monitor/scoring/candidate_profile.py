"""Candidate Profile model and loader supporting candidate-specific job intelligence configuration."""

import os
from pathlib import Path
from typing import Any, List, Optional, Set
import yaml
from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    """Candidate profile encapsulating candidate background, skills, target roles, and scoring preferences."""
    id: str = "ann"
    name: str = "Ann"
    professional_title: str = "Backend & API Engineer"
    location_country: str = "Nigeria"
    timezone_region: str = "WAT/EMEA"
    total_years_experience: float = 6.0
    minimum_salary_usd: Optional[float] = 80000.0
    minimum_hourly_usd: Optional[float] = 40.0

    # Skills taxonomy
    primary_skills: Set[str] = Field(
        default_factory=lambda: {
            "java", "spring boot", "spring security", "rest api", "rest apis", "restful",
            "postgresql", "postgres", "sql", "hibernate", "jpa", "backend", "api development",
            "api integration", "microservices", "git", "junit", "mockito", "docker", "aws"
        }
    )

    additional_skills: Set[str] = Field(
        default_factory=lambda: {
            "javascript", "typescript", "node.js", "nodejs", "node", "nestjs", "express",
            "express.js", "next.js", "nextjs", "mongodb", "html", "css", "html/css",
            "thymeleaf", "heroku", "openapi", "swagger", "postman", "payment apis",
            "payment integration"
        }
    )

    transferable_skills: Set[str] = Field(
        default_factory=lambda: {
            "python", "golang", "go lang", "go developer", "go engineer", "go backend",
            "fastapi", "graphql", "grpc", "redis", "kafka", "rabbitmq", "elasticsearch",
            "kubernetes", "k8s", "terraform", "azure", "gcp"
        }
    )

    secondary_skills: Set[str] = Field(
        default_factory=lambda: {
            "ai model evaluation", "ai annotation", "data annotation", "ai training",
            "technical ai trainer", "technical evaluation", "code evaluation", "code review",
            "project management", "scrum", "requirements gathering", "business analysis",
            "technical documentation", "api documentation", "technical writing", "research",
            "editing", "proofreading"
        }
    )

    # Target titles & domains
    target_titles: Set[str] = Field(
        default_factory=lambda: {
            "backend engineer", "backend developer", "software engineer - backend",
            "software engineer, backend", "java developer", "java backend engineer",
            "spring boot engineer", "spring boot developer", "api engineer", "api developer",
            "microservices engineer", "integration engineer", "platform engineer",
            "backend platform engineer", "senior software engineer", "mid-level software engineer"
        }
    )

    target_roles: Set[str] = Field(default_factory=set)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.target_roles:
            self.target_titles.update(self.target_roles)
        if self.target_titles:
            self.target_roles.update(self.target_titles)

    preferred_domains: Set[str] = Field(
        default_factory=lambda: {
            "fintech", "payments", "banking", "saas", "enterprise", "e-commerce", "ecommerce",
            "logistics", "healthtech", "agritech", "edtech", "insurtech", "proptech", "ai",
            "developer tools", "cybersecurity", "cloud infrastructure", "telecommunications",
            "marketplace", "b2b", "startups"
        }
    )

    preferred_locations: Set[str] = Field(
        default_factory=lambda: {"Worldwide", "EMEA", "Nigeria"}
    )

    eligible_countries: Set[str] = Field(
        default_factory=lambda: {"Worldwide", "EMEA", "Nigeria"}
    )

    preferred_employment_types: List[str] = Field(
        default_factory=lambda: ["full_time", "contract", "fractional"]
    )

    fast_cash_keywords: Set[str] = Field(
        default_factory=lambda: {"immediate", "urgent", "asap", "contract", "short-term", "hourly"}
    )

    # Configurable Pattern Lists for Title Matching
    target_title_patterns: List[str] = Field(
        default_factory=lambda: [
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
    )

    non_target_title_patterns: List[str] = Field(
        default_factory=lambda: [
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
    )

    technical_evidence_patterns: List[str] = Field(
        default_factory=lambda: [
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
    )


def load_candidate_profile(profile_name_or_path: str = "ann") -> CandidateProfile:
    """Loads a CandidateProfile by name ('ann', 'cloud_engineer') or path to YAML file."""
    from ..utils.paths import AppPaths
    embedded = AppPaths.get_embedded_profile_path()
    if embedded and embedded.exists():
        return _load_yaml_profile(embedded)

    if not profile_name_or_path:
        return get_default_candidate_profile()

    # 1. If it's an existing YAML path
    candidate_path = Path(profile_name_or_path)
    if candidate_path.exists() and candidate_path.is_file():
        return _load_yaml_profile(candidate_path)

    # 2. Check profiles directory relative to project root
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    profile_filename = profile_name_or_path if profile_name_or_path.endswith(".yaml") else f"{profile_name_or_path}.yaml"
    
    possible_paths = [
        base_dir / "profiles" / profile_filename,
        base_dir / "profiles" / f"example_{profile_name_or_path}.yaml",
        Path.cwd() / "profiles" / profile_filename,
    ]

    for p in possible_paths:
        if p.exists() and p.is_file():
            return _load_yaml_profile(p)

    # Default fallback to Ann's profile
    return get_default_candidate_profile()


def _load_yaml_profile(filepath: Path) -> CandidateProfile:
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return get_default_candidate_profile()
        
        # Convert list fields to sets where expected by CandidateProfile
        set_fields = [
            "primary_skills", "additional_skills", "transferable_skills",
            "secondary_skills", "target_titles", "target_roles", "preferred_domains",
            "preferred_locations", "eligible_countries", "fast_cash_keywords"
        ]
        for field in set_fields:
            if field in data and isinstance(data[field], list):
                data[field] = set(data[field])

        return CandidateProfile(**data)


def get_default_candidate_profile() -> CandidateProfile:
    """Returns baseline default candidate profile for Ann."""
    return CandidateProfile()
