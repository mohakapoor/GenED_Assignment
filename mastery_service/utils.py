from fastapi import HTTPException, Depends, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mastery_service.seed_data import TOKENS, TEACHER_ROSTERS

from mastery_service.config import EMA_ALPHA

def calculate_new_mastery(current_score: float, is_correct: bool) -> float:
    """
    Calculates the new mastery score using an Exponential Moving Average (EMA).
    Formula: (current_score * (1 - EMA_ALPHA)) + (attempt_score * EMA_ALPHA)
    This smoothly approaches 100 asymptotically, self-balances, and requires no history state!
    """
    attempt_score = 100.0 if is_correct else 0.0
    new_score = (current_score * (1.0 - EMA_ALPHA)) + (attempt_score * EMA_ALPHA)
        
    # Clamp between 0 and 100 and round to 2 decimals for clean storage
    return max(0.0, min(100.0, round(new_score, 2)))

security = HTTPBearer()

def get_current_identity(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Resolve the Authorization header into {"role", "user_id"}."""
    token = credentials.credentials
    identity = TOKENS.get(token)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return identity

def verify_access(
    student_id: str = Path(...), 
    identity: dict = Depends(get_current_identity)
) -> str:
    """Verifies the current user is allowed to access data for student_id."""
    role = identity["role"]
    user_id = identity["user_id"]
    
    if role == "STUDENT":
        if user_id != student_id:
            raise HTTPException(status_code=403, detail="You can only view your own data.")
            
    elif role == "TEACHER":
        roster = TEACHER_ROSTERS.get(user_id, [])
        if student_id not in roster:
            raise HTTPException(status_code=403, detail="Student not in your roster.")
            
    else:
        raise HTTPException(status_code=403, detail="Unknown role.")
        
    return student_id

def verify_student_only_access(
    student_id: str = Path(...), 
    identity: dict = Depends(get_current_identity)
) -> str:
    """Verifies that the current user is exclusively the student_id in the path."""
    role = identity["role"]
    user_id = identity["user_id"]
    
    if role != "STUDENT" or user_id != student_id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this student's data.")
        
    return student_id
