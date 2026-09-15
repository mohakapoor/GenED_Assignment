from pydantic import BaseModel
from datetime import datetime
from typing import List

class AttemptRequest(BaseModel):
    skill_id: str
    is_correct: bool

class AttemptResponse(BaseModel):
    skill_id: str
    is_correct: bool
    new_score: float
    feedback: str

class MasteryItem(BaseModel):
    skill_id: str
    score: float

class NotificationItem(BaseModel):
    id: int
    skill_id: str
    milestone: int
    created_at: datetime

class MasteryResponse(BaseModel):
    status: str
    data: List[MasteryItem]

class NotificationResponse(BaseModel):
    status: str
    data: List[NotificationItem]
