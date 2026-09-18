import sqlite3
from pathlib import Path

DB_PATH = Path("./research.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    title TEXT,
    content TEXT,
    hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    priority TEXT,
    status TEXT,
    description TEXT,
    doc_id INTEGER,
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL UNIQUE,
    action_hash TEXT,
    verdict TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patterns_name ON patterns(name);
CREATE INDEX IF NOT EXISTS idx_verdicts_hash ON verdicts(action_hash);
"""

# SECURITY FIX: Add is_authoritative column to existing verdicts tables.
# This migration is idempotent — it silently skips if the column already exists.
_MIGRATION_ADD_AUTHORITATIVE = """
    ALTER TABLE verdicts ADD COLUMN is_authoritative INTEGER NOT NULL DEFAULT 1;
"""

def main():
    # Remove existing database if any to start fresh? But we want to preserve if exists.
    # We'll just connect and execute schema.
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        # Apply migration
        try:
            conn.execute(_MIGRATION_ADD_AUTHORITATIVE)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
        conn.commit()
        print(f"Database initialized at {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()