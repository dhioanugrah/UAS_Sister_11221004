from pydantic import BaseModel, Field
from typing import Any, Dict, List
from datetime import datetime

class Event(BaseModel):
    topic: str = Field(min_length=1, max_length=128)
    event_id: str = Field(min_length=8, max_length=256)
    timestamp: datetime
    source: str = Field(min_length=1, max_length=128)
    payload: Dict[str, Any]

class PublishRequest(BaseModel):
    events: List[Event]
