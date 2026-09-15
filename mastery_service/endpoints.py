import sqlite3
from fastapi import HTTPException
from mastery_service.models import AttemptRequest, AttemptResponse
from mastery_service.utils import calculate_new_mastery
from mastery_service.seed_data import SKILL_IDS

def process_attempt(db: sqlite3.Connection, student_id: str, request: AttemptRequest) -> AttemptResponse:
    """Handles the business logic and database orchestration for a new attempt."""
    

    if request.skill_id not in SKILL_IDS:
        raise HTTPException(status_code=400, detail="Invalid skill_id")
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

    # 6. Return response
    return AttemptResponse(
        skill_id=request.skill_id,
        is_correct=request.is_correct,
        new_score=new_score,
        feedback="Mastery updated! AI feedback and milestones coming next."
    )
