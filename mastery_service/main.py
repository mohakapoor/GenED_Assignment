"""
STARTER FILE — build the actual service here (or restructure into more
files/modules if you prefer; this single-file skeleton is just a starting
point, not a requirement).

See PROBLEM.md for the full spec. Summary of what needs to exist by the end:

  POST /students/{student_id}/attempts
      Body: {"skill_id": str, "is_correct": bool}
      - Only the student themselves may submit their own attempts.
      - Updates that student's mastery score (0-100) for that skill using a
        scoring approach YOU design and justify in WRITEUP.md.
      - Calls get_ai_feedback() (see ai_feedback.py) to get a feedback
        string for the response. That call is slow and sometimes fails —
        your endpoint must still behave well when it does.
      - Enforces: max 30 attempts per student per rolling 24h. A request
        that fails validation (bad skill_id, malformed body, etc.) must NOT
        count against that limit.
      - If this attempt takes the student's mastery for that skill above 80
        for the first time, a milestone notification must be durably
        recorded — including surviving a crash between "mastery updated"
        and "notification recorded."

  GET /students/{student_id}/mastery
      - A student may view their own mastery.
      - A teacher may view mastery for any student on their own roster
        (see seed_data.TEACHER_ROSTERS), and no one else's.
      - Returns current mastery per skill for that student.

  GET /notifications/{student_id}
      - Same access rule as above. Returns the milestone notifications
        recorded for that student.

Everything below this docstring is scaffolding, not a solution — feel free
to delete, restructure, or heavily rewrite it.
"""

from fastapi import FastAPI, Header, HTTPException, Depends, Query
import uvicorn
import sqlite3
from typing import List

from mastery_service.utils import (
    get_current_identity, 
    verify_access, 
    verify_student_only_access,
    verify_teacher_only_access
)
from mastery_service.database import get_db, init_db
from mastery_service.models import (
    AttemptRequest, AttemptResponse, 
    MasteryResponse, NotificationResponse,
    RosterSummaryResponse
)
import mastery_service.endpoints as endpoints

app = FastAPI(title="GenEd Mastery Service — Take-Home")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/api_name")
def api_name() -> dict:
    return {"name": "GenEd Mastery Service"}


@app.get("/identity")
def identity(identity: dict = Depends(get_current_identity)) -> dict:
    return identity

@app.get("/has_access/{student_id}")
def test_has_access(student_id: str = Depends(verify_access)) -> dict:
    return {"message": f"You have access to student: {student_id}"}

@app.post("/students/{student_id}/attempts", response_model=AttemptResponse)
def create_attempt(
    request: AttemptRequest,
    student_id: str = Depends(verify_student_only_access),
    db: sqlite3.Connection = Depends(get_db)
):
    return endpoints.process_attempt(db, student_id, request)

@app.get("/students/{student_id}/mastery", response_model=MasteryResponse)
def read_mastery(
    student_id: str = Depends(verify_access),
    db: sqlite3.Connection = Depends(get_db)
):
    return endpoints.get_student_mastery(db, student_id)

@app.get("/notifications/{student_id}", response_model=NotificationResponse)
def get_student_notifications(
    student_id: str = Depends(verify_access),
    db: sqlite3.Connection = Depends(get_db)
):
    """Fetch milestone notifications for a student."""
    return endpoints.get_student_notifications(db, student_id)

@app.get("/teachers/{teacher_id}/summary", response_model=RosterSummaryResponse)
def get_teacher_roster_summary(
    teacher_id: str = Depends(verify_teacher_only_access), 
    limit: int = Query(5, ge=1, le=50),
    db: sqlite3.Connection = Depends(get_db)
):
    """Fetch a paginated summary of a teacher's roster, sorted by lowest mastery first."""
    return endpoints.get_roster_summary(db, teacher_id, limit)

if __name__ == "__main__":
    uvicorn.run("mastery_service.main:app", host="127.0.0.1", port=8000, reload=True)
