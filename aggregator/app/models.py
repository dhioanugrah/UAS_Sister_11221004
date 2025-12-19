from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any
from datetime import datetime

class Event(BaseModel):
    topic: str = Field(min_length=1)
    event_id: str = Field(min_length=5)
    timestamp: datetime
    source: str
    payload: Dict[str, Any]

class PublishRequest(BaseModel):
    events: List[Event]

    @field_validator("events")
    @classmethod
    def events_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("events array must not be empty")
        return v
