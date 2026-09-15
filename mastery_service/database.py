import sqlite3
from contextlib import contextmanager
from pathlib import Path

from mastery_service.seed_data import STUDENT_IDS, SKILL_IDS, TEACHER_ROSTERS

# Store the database file in the mastery_service directory
DB_PATH = Path(__file__).parent / "mastery.db"

@contextmanager
def get_db():
    """Provide a transactional scope around a series of database operations."""
    # check_same_thread=False 
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize the database schema with the core tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create Teachers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id TEXT PRIMARY KEY
            )
        """)
        
        # Create Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY
            )
        """)
        
        # Create Skills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY
            )
        """)
        
        # Create Mastery table (Composite Primary Key)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mastery (
                student_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0.0 CHECK (score >= 0 AND score <= 100),
                PRIMARY KEY (student_id, skill_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Create Attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Create Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                milestone INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id),
                UNIQUE (student_id, skill_id, milestone)
            )
        """)
        
        # Create composite index for rate limiting queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_student_time 
            ON attempts (student_id, attempted_at)
        """)
        
        # Commit the transaction
        conn.commit()

def seed_db():
    with get_db() as conn:
        cursor = conn.cursor()

        for student_id in STUDENT_IDS:
            cursor.execute("INSERT OR IGNORE INTO students (id) VALUES (?)", (student_id,))
            
        # Insert Teachers
        for teacher_id in TEACHER_ROSTERS.keys():
            cursor.execute("INSERT OR IGNORE INTO teachers (id) VALUES (?)", (teacher_id,))
            
        # Insert Skills
        for skill_id in SKILL_IDS:
            cursor.execute("INSERT OR IGNORE INTO skills (id) VALUES (?)", (skill_id,))
            
        conn.commit()

if __name__ == "__main__":
    init_db()
    seed_db()
    print(f"DB Initialized")
