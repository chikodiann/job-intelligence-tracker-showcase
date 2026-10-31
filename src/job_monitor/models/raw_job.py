from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RawJob(BaseModel):
    """Container for unparsed, source-native job payload."""
    source_name: str
    external_id: str
    payload: Dict[str, Any]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
