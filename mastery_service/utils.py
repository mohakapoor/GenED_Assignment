from fastapi import HTTPException, Depends, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mastery_service.seed_data import TOKENS, TEACHER_ROSTERS

def calculate_new_mastery(current_score: float, is_correct: bool) -> float:
    """
    Placeholder mastery formula:
    - Adds 10 points if the attempt is correct.
    - Subtracts 2 points if the attempt is incorrect.
    - Clamps the final score between 0.0 and 100.0.
    """
    if is_correct:
        new_score = current_score + 10.0
    else:
        new_score = current_score - 2.0
        
    # Clamp between 0 and 100 so we don't violate the DB constraint
    return max(0.0, min(100.0, new_score))

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
