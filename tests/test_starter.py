"""
Given smoke tests, so you know the skeleton runs before you start.

These are NOT the tests your submission will be judged by — write your own
covering the tricky bits (the crash-during-notification requirement, the
rate-limit edge case, the flaky AI dependency). Feel free to add
tests/conftest.py, more test files, fixtures, whatever you'd normally set up.
"""

import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch


import mastery_service.database as db_module
TEST_DB_PATH = Path(__file__).parent / "test_mastery.db"
db_module.DB_PATH = TEST_DB_PATH

from mastery_service.main import app
db_module.init_db()
db_module.seed_db()

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unknown_token_rejected():
    # Replace/extend once your endpoints exist — this just proves the
    # scaffolding's auth resolver plugs into a real route.
    response = client.get(
        "/students/student-ananya/mastery",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code in (401, 404)  # 404 until you build the route







def test_get_student_mastery_forbidden():
    headers = {"Authorization": "Bearer token-student-rohan"}
    response = client.get("/students/student-mei/mastery", headers=headers)
    assert response.status_code == 403












def test_rate_limit_boundary():
    with sqlite3.connect(TEST_DB_PATH) as conn:
        conn.execute("DELETE FROM attempts WHERE student_id = 'student-mei'")
        

        for _ in range(30):
            conn.execute(
                "INSERT INTO attempts (student_id, skill_id, is_correct) VALUES (?, ?, ?)",
                ("student-mei", "math.fractions.add-subtract", True)
            )
        conn.commit()

    headers = {"Authorization": "Bearer token-student-mei"}
    payload = {"skill_id": "math.fractions.add-subtract", "is_correct": False}

    response = client.post("/students/student-mei/attempts", headers=headers, json=payload)
    
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]














def test_flaky_ai_fallback():
    """Test that a failing AI provider still returns a 200 OK with the fallback string."""
    headers = {"Authorization": "Bearer token-student-rohan"}
    payload = {"skill_id": "math.fractions.add-subtract", "is_correct": True}

    # We use @patch to force the AI function to instantly crash, saving us 5 seconds!
    with patch('mastery_service.endpoints.get_ai_feedback') as mock_ai:
        from mastery_service.ai_feedback import AIFeedbackError
        mock_ai.side_effect = AIFeedbackError("Simulated AI Timeout")
        
        response = client.post("/students/student-rohan/attempts", headers=headers, json=payload)
        
        assert response.status_code == 200
        assert response.json()["feedback"] == "AI feedback temporarily unavailable."

















def test_crash_during_notification_rollback():

    
    with sqlite3.connect(TEST_DB_PATH) as conn:
        conn.execute("DELETE FROM mastery WHERE student_id = 'student-rohan'")
        conn.execute(
            "INSERT INTO mastery (student_id, skill_id, score) VALUES (?, ?, ?)",
            ("student-rohan", "math.fractions.add-subtract", 79.0)
        )
        conn.commit()
        
        # simulate a crash by dropping the table
        conn.execute("DROP TABLE notifications")

    try:
        headers = {"Authorization": "Bearer token-student-rohan"}
        payload = {"skill_id": "math.fractions.add-subtract", "is_correct": True}
        
        import pytest
        
        # expect this crash
        with pytest.raises(sqlite3.OperationalError, match="no such table: notifications"):
            client.post("/students/student-rohan/attempts", headers=headers, json=payload)
        
        # Verify the rollback
        with sqlite3.connect(TEST_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT score FROM mastery WHERE student_id = ? AND skill_id = ?", 
                ("student-rohan", "math.fractions.add-subtract")
            ).fetchone()
            
            assert row["score"] == 79.0
    finally:
        db_module.init_db()
