"""Database migration — add daily_matches table.

Usage:
    cd twintalk/backend
    python migrations/add_daily_match_table.py
"""

import os
import sqlite3

# Resolve the default DB path
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///digital_twin.db")
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "")

# Determine absolute path relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # twintalk/backend
DB_FILE = os.path.join(PROJECT_ROOT, DB_PATH)

def migrate():
    print(f"Migrating database at: {DB_FILE}")
    if not os.path.exists(DB_FILE):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        print("Creating table 'daily_matches'...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_matches (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            candidate_id VARCHAR(36) NOT NULL,
            score FLOAT DEFAULT 0.0,
            match_reason TEXT DEFAULT '',
            score_breakdown JSON DEFAULT '{}',
            profile_tags JSON DEFAULT '[]',
            common_interests JSON DEFAULT '[]',
            bio_third_view TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(candidate_id) REFERENCES users(id)
        );
        """)
        
        print("Creating index on user_id...")
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_daily_matches_user_id ON daily_matches (user_id);
        """)

        conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
