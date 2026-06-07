import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'students.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            email TEXT NOT NULL,
            phone_number TEXT,
            department TEXT NOT NULL,
            interested_domains TEXT NOT NULL,
            events TEXT NOT NULL,
            suggestions TEXT,
            expectations TEXT,
            rating INTEGER,
            involvement_interest TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def migrate_db():
    """Add new columns to existing database if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing = [row[1] for row in cursor.execute("PRAGMA table_info(students)").fetchall()]
    if 'phone_number' not in existing:
        cursor.execute("ALTER TABLE students ADD COLUMN phone_number TEXT")
    if 'suggestions' not in existing:
        cursor.execute("ALTER TABLE students ADD COLUMN suggestions TEXT")
    if 'expectations' not in existing:
        cursor.execute("ALTER TABLE students ADD COLUMN expectations TEXT")
    if 'rating' not in existing:
        cursor.execute("ALTER TABLE students ADD COLUMN rating INTEGER")
    if 'involvement_interest' not in existing:
        cursor.execute("ALTER TABLE students ADD COLUMN involvement_interest TEXT")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
