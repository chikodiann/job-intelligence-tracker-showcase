from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SalaryPeriod(str, Enum):
    HOURLY = "hourly"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    UNKNOWN = "unknown"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FRACTIONAL = "fractional"
    INTERNSHIP = "internship"
    UNKNOWN = "unknown"


class NormalizedJob(BaseModel):
    """Canonical representation of a job posting across all ingestion feeds."""
    id: Optional[str] = None  # UUID or database primary key
    source_name: str
    external_id: str
    url: str
    title: str
    company_name: str
    is_remote: bool = True
    location_requirement: Optional[str] = "Worldwide"
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    
    # Financial / Cashflow Data
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: SalaryPeriod = SalaryPeriod.UNKNOWN
    annualized_min_usd: Optional[float] = None
    annualized_max_usd: Optional[float] = None
    original_salary_text: Optional[str] = None

    # Descriptive Data
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description_raw: str = ""
    description_text: str = ""
    
    # Fingerprinting & Metadata
    content_hash: str = ""
    canonical_fingerprint: str = ""
    posted_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_verified_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "ACTIVE"  # ACTIVE, ARCHIVED, EXPIRED
    review_state: str = "UNREVIEWED"  # UNREVIEWED, REVIEWING, DISMISSED
    applied_at: Optional[datetime] = None
