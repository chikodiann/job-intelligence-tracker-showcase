from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .normalized_job import EmploymentType


class CashflowObjective(str, Enum):
    FAST_CASH = "FAST_CASH"        # Prioritize fast income generation
    STABLE_CAREER = "STABLE_CAREER" # Prioritize long-term remote employment
    BALANCED = "BALANCED"           # Balanced scoring


class CashflowProfile(BaseModel):
    """User financial preferences and search objective profile.
    
    NOTE: Compensation targets (target_annual_cashflow, target_hourly_rate) are strictly
    used for candidate ranking/scoring in Phase 3. They MUST NEVER be used as hard eligibility
    filters to discard jobs. Jobs with missing or low compensation remain fully valid.
    """
    profile_name: str = "Default Profile"
    target_currency: str = "USD"
    cashflow_objective: CashflowObjective = CashflowObjective.BALANCED
    target_annual_cashflow: Optional[float] = None
    target_hourly_rate: Optional[float] = None
    desired_employment_types: List[EmploymentType] = Field(
        default_factory=lambda: [EmploymentType.FULL_TIME, EmploymentType.CONTRACT, EmploymentType.FRACTIONAL]
    )
    required_keywords: List[str] = Field(default_factory=list)
    preferred_keywords: List[str] = Field(default_factory=list)
    excluded_keywords: List[str] = Field(default_factory=list)
