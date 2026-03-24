"""Database migration — add new columns for memory refactor v2.

Run this script once to add the new columns to existing tables.
Safe to re-run: uses IF NOT EXISTS / TRY approach.

Usage:
    cd twintalk/backend
    python migrations/add_memory_columns.py
"""

import os
import sys
import sqlite3

# Resolve the default DB path
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///digital_twin.db")
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "")

# Also check from backend folder context
if not os.path.isabs(DB_PATH):
    candidates = [
        DB_PATH,
        os.path.join(os.path.dirname(__file__), "..", DB_PATH),
        os.path.join(os.path.dirname(__file__), "..", "..", DB_PATH),
    ]
    for c in candidates:
        if os.path.exists(c):
            DB_PATH = c
            break


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def migrate():
    print(f"Connecting to: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations = [
        ("key_memories", "embedding", "BLOB"),
        ("conversation_memories", "session_summary", "TEXT DEFAULT ''"),
    ]

    applied = 0
    for table, column, col_type in migrations:
        if not column_exists(cursor, table, column):
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            print(f"  + {sql}")
            cursor.execute(sql)
            applied += 1
        else:
            print(f"  ✓ {table}.{column} already exists")

    conn.commit()
    conn.close()
    print(f"\nMigration complete. {applied} column(s) added.")


if __name__ == "__main__":
    migrate()
