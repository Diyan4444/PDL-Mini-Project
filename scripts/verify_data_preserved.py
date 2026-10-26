import sqlite3
import os
from pathlib import Path

DB_PATH = Path("data/exam_predictor.db")

def check_counts():
    if not DB_PATH.exists():
        print(f"Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = ["subjects", "papers", "questions", "mcq_bank", "student_attempts"]
    counts = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = "table_missing"
            
    conn.close()
    
    print("Database Row Counts:")
    for table, count in counts.items():
        print(f"  {table}: {count}")
        
    expected = {
        "subjects": 4,
        "papers": 6,
        "questions": 52,
        "mcq_bank": 98,
        "student_attempts": 0
    }
    
    print("\nComparison against expected baselines:")
    all_ok = True
    for t, exp in expected.items():
        actual = counts.get(t, 0)
        status = "OK" if isinstance(actual, int) and actual >= exp else "FAIL"
        if status == "FAIL":
            all_ok = False
        print(f"  {t}: {actual} (expected >= {exp}) -> {status}")
        
    return all_ok

if __name__ == "__main__":
    check_counts()
