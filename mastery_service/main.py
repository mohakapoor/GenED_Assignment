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

from fastapi import FastAPI, Header, HTTPException, Depends, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

from mastery_service.seed_data import TOKENS, TEACHER_ROSTERS

app = FastAPI(title="GenEd Mastery Service — Take-Home")

security = HTTPBearer()

def get_current_identity(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Resolve the Authorization header into {"role", "user_id"}.

    This is deliberately trivial — see seed_data.py for how the token map
    works. Raise HTTPException(401) for a missing/unknown token.
    """
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

# TODO: POST /students/{student_id}/attempts
# TODO: GET /students/{student_id}/mastery
# TODO: GET /notifications/{student_id}

if __name__ == "__main__":
    uvicorn.run("mastery_service.main:app", host="127.0.0.1", port=8000, reload=True)
