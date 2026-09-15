from fastapi import HTTPException, Depends, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mastery_service.seed_data import TOKENS, TEACHER_ROSTERS

from mastery_service.config import EMA_ALPHA

def calculate_new_mastery(current_score: float, is_correct: bool) -> float:

    attempt_score = 100.0 if is_correct else 0.0
    new_score = (current_score * (1.0 - EMA_ALPHA)) + (attempt_score * EMA_ALPHA)
        
    return new_score

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

    role = identity["role"]
    user_id = identity["user_id"]
    
    if role == "STUDENT":
        if user_id != student_id:
            raise HTTPException(status_code=403, detail="You can only view your own data.")
            
    elif role == "TEACHER":
        roster = TEACHER_ROSTERS.get(user_id, [])
        if student_id not in roster:
            raise HTTPException(status_code=403, detail="Student not in your roster")
            
    else:
        raise HTTPException(status_code=403, detail="Unknown role.")
        
    return student_id

def verify_teacher_only_access(
    teacher_id: str = Path(...),
    identity: dict = Depends(get_current_identity)
) -> str:

    if identity["role"] != "TEACHER":
        raise HTTPException(status_code=403, detail="Only teachers can access this endpoint")
    if identity["user_id"] != teacher_id:
        raise HTTPException(status_code=403, detail="You can only access your own roster summary")
    return identity["user_id"]
    

def verify_student_only_access(
    student_id: str = Path(...), 
    identity: dict = Depends(get_current_identity)
) -> str:

    role = identity["role"]
    user_id = identity["user_id"]
    
    if role != "STUDENT" or user_id != student_id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this student's data.")
        
    return student_id
