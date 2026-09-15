import sqlite3
import time
from typing import List
from fastapi import HTTPException
from mastery_service.models import (
    AttemptRequest, AttemptResponse, 
    MasteryItem, MasteryResponse,
    NotificationItem, NotificationResponse,
    StudentSummary, RosterSummaryResponse
)


from mastery_service.utils import calculate_new_mastery
from mastery_service.seed_data import SKILL_IDS, TEACHER_ROSTERS
from mastery_service.ai_feedback import get_ai_feedback, AIFeedbackError

from mastery_service.config import RATE_LIMIT_MAX_ATTEMPTS, RATE_LIMIT_WINDOW_HOURS, MILESTONE_THRESHOLD



def process_attempt(db: sqlite3.Connection, student_id: str, request: AttemptRequest) -> AttemptResponse:
    """Handles the business logic and database orchestration for a new attempt."""

    # Validation of skills
    if request.skill_id not in SKILL_IDS:
        raise HTTPException(status_code=400, detail="Invalid skill_id")
    
    # Rate Limiting Check
    window_seconds = RATE_LIMIT_WINDOW_HOURS * 60 * 60
    window_start = int(time.time()) - window_seconds
    count_row = db.execute(
        "SELECT COUNT(*) as c FROM attempts WHERE student_id = ? AND attempted_at >= ?",
        (student_id, window_start)
    ).fetchone()
    
    if count_row["c"] >= RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. You can only make {RATE_LIMIT_MAX_ATTEMPTS} attempts per rolling {RATE_LIMIT_WINDOW_HOURS} hours."
        )
    row = db.execute(
        "SELECT score FROM mastery WHERE student_id = ? AND skill_id = ?",
        (student_id, request.skill_id)
    ).fetchone()
    
    current_score = row["score"] if row else 0.0
    new_score = calculate_new_mastery(current_score, request.is_correct)

    db.execute(
        "INSERT INTO attempts (student_id, skill_id, is_correct) VALUES (?, ?, ?)",
        (student_id, request.skill_id, request.is_correct)
    )
    
    db.execute(
        """
        INSERT INTO mastery (student_id, skill_id, score) 
        VALUES (?, ?, ?)
        ON CONFLICT(student_id, skill_id) DO UPDATE SET score = excluded.score
        """,
        (student_id, request.skill_id, new_score)
    )

    if new_score > MILESTONE_THRESHOLD:
        db.execute(
            """
            INSERT OR IGNORE INTO notifications (student_id, skill_id, milestone)
            VALUES (?, ?, ?)
            """,
            (student_id, request.skill_id, MILESTONE_THRESHOLD)
        )

    # Commit early!
    db.commit()


    try:
        feedback = get_ai_feedback(request.skill_id, request.is_correct)
    except AIFeedbackError:
        feedback = "AI feedback temporarily unavailable."

    return AttemptResponse(
        skill_id=request.skill_id,
        is_correct=request.is_correct,
        new_score=new_score,
        feedback=feedback
    )

def get_student_mastery(db: sqlite3.Connection, student_id: str) -> MasteryResponse:
    """Retrieves all current mastery scores for a specific student."""


    rows = db.execute(
        "SELECT skill_id, score FROM mastery WHERE student_id = ?",
        (student_id,)
    ).fetchall()
    
    items = [MasteryItem(skill_id=row["skill_id"], score=row["score"]) for row in rows]
    status = "Records found" if items else "No records yet"
    
    return MasteryResponse(status=status, data=items)

def get_student_notifications(db: sqlite3.Connection, student_id: str) -> NotificationResponse:
    """Retrieves all milestone notifications for a specific student."""


    rows = db.execute(
        "SELECT id, skill_id, milestone, created_at FROM notifications WHERE student_id = ?",
        (student_id,)
    ).fetchall()
    
    items = [
        NotificationItem(
            id=row["id"], 
            skill_id=row["skill_id"], 
            milestone=row["milestone"], 
            created_at=row["created_at"]
        ) 
        for row in rows
    ]
    
    status = "Records found" if items else "No records yet"
    return NotificationResponse(status=status, data=items)

def get_roster_summary(db: sqlite3.Connection, teacher_id: str, limit: int) -> RosterSummaryResponse:
    """Gets the roster summary for a teacher, sorted by lowest average mastery."""


    roster = TEACHER_ROSTERS.get(teacher_id, [])
    if not roster:
        return RosterSummaryResponse(status="No records yet", data=[])
    
    placeholders = ",".join(["?"] * len(roster))
    
    query = f"""
        SELECT student_id, AVG(score) as average_mastery, COUNT(skill_id) as skills_attempted
        FROM mastery 
        WHERE student_id IN ({placeholders})
        GROUP BY student_id
        ORDER BY average_mastery ASC
        LIMIT ?
    """
    
    params = tuple(roster) + (limit,)
    rows = db.execute(query, params).fetchall()
    
    data = []
    for row in rows:
        data.append(StudentSummary(
            student_id=row["student_id"],
            average_mastery=round(row["average_mastery"], 2),
            skills_attempted=row["skills_attempted"]
        ))
        
    status = "Records found" if data else "No records yet"
    return RosterSummaryResponse(status=status, data=data)
