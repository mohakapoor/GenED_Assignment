import sqlite3
import time
from typing import List
from fastapi import HTTPException
from mastery_service.models import (
    AttemptRequest, AttemptResponse, 
    MasteryItem, MasteryResponse,
    NotificationItem, NotificationResponse
)
from mastery_service.utils import calculate_new_mastery
from mastery_service.seed_data import SKILL_IDS
from mastery_service.ai_feedback import get_ai_feedback, AIFeedbackError

def process_attempt(db: sqlite3.Connection, student_id: str, request: AttemptRequest) -> AttemptResponse:
    """Handles the business logic and database orchestration for a new attempt."""

    # Validate input BEFORE doing any DB rate-limit checks
    if request.skill_id not in SKILL_IDS:
        raise HTTPException(status_code=400, detail="Invalid skill_id")
    
    # 1. Rate Limiting Check (max 30 attempts per student per rolling 24 hours)
    yesterday = int(time.time()) - (24 * 60 * 60)
    count_row = db.execute(
        "SELECT COUNT(*) as c FROM attempts WHERE student_id = ? AND attempted_at >= ?",
        (student_id, yesterday)
    ).fetchone()
    
    if count_row["c"] >= 30:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. You can only make 30 attempts per rolling 24 hours."
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

    # Commit early to release the SQLite write lock before the slow AI call!
    db.commit()

    # 6. Fetch AI Feedback
    try:
        feedback = get_ai_feedback(request.skill_id, request.is_correct)
    except AIFeedbackError:
        feedback = "AI feedback temporarily unavailable."

    # 7. Return response
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
