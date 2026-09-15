import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Store the database file in the mastery_service directory
DB_PATH = Path(__file__).parent / "mastery.db"

@contextmanager
def get_db():
    """Provide a transactional scope around a series of database operations."""
    # check_same_thread=False is needed for FastAPI since it might use 
    # different threads for different requests
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Enable foreign key constraint enforcement
    conn.execute("PRAGMA foreign_keys = ON;")
    # This allows us to access columns by name (e.g., row['id'])
    conn.row_factory = sqlite3.Row
    try:
        yield conn
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
                student_id TEXT,
                skill_id TEXT,
                score REAL,
                PRIMARY KEY (student_id, skill_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Create Attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                skill_id TEXT,
                is_correct BOOLEAN,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Create Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                skill_id TEXT,
                milestone INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        # Create composite index for rate limiting queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_student_time 
            ON attempts (student_id, attempted_at)
        """)
        
        # Commit the transaction
        conn.commit()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
