from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    ACCEPTED = "ACCEPTED"


class InterviewStage(str, Enum):
    NONE = "NONE"
    STAGE_1 = "STAGE_1"
    STAGE_2 = "STAGE_2"
    STAGE_3 = "STAGE_3"
    FINAL = "FINAL"
    OTHER = "OTHER"


class Application(BaseModel):
    """Represents a candidate's formal job application interaction & lifecycle."""
    id: Optional[str] = None
    job_id: str
    status: ApplicationStatus = ApplicationStatus.APPLIED
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    interview_stage: InterviewStage = InterviewStage.NONE
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApplicationStatusHistory(BaseModel):
    """Represents a historical status change event for an application."""
    id: Optional[str] = None
    application_id: str
    status: ApplicationStatus
    interview_stage: InterviewStage = InterviewStage.NONE
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

