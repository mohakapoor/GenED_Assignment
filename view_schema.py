import sqlite3
from pathlib import Path

# Path to the mastery.db created by database.py
DB_PATH = Path(__file__).parent / "mastery_service" / "mastery.db"

def show_schema():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query sqlite_master to get all tables and their CREATE TABLE statements
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()
    
    if not tables:
        print("No tables found in the database.")
    else:
        print(f"Found {len(tables)} tables:\n")
        for table_name, schema in tables:
            print(f"=== Table: {table_name} ===")
            print(f"{schema}")
            
            # Fetch up to 5 rows
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                if rows:
                    print("\nSample Data (up to 5 rows):")
                    for row in rows:
                        print(f"  {row}")
                else:
                    print("\nSample Data: (Empty)")
            except Exception as e:
                print(f"\nError fetching data: {e}")
                
            print("\n" + "-"*40 + "\n")
            
    conn.close()

if __name__ == "__main__":
    show_schema()
