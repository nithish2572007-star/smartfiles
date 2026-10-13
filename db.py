import os
import sqlite3
from typing import Any, Dict, List, Optional

DB_FILE = os.environ.get("SMARTFILES_DB", "smartfiles.db")

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str = DB_FILE) -> None:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_path TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT CHECK(status IN ('in_progress', 'completed', 'cancelled', 'failed')) DEFAULT 'in_progress',
                total_scanned INTEGER DEFAULT 0,
                error_log TEXT,
                skipped_items TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                ext TEXT NOT NULL,
                category TEXT NOT NULL,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                sha256 TEXT,
                FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256);")
        # Run migration if skipped_items column is missing in an existing database
        cursor.execute("PRAGMA table_info(scans);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "skipped_items" not in columns:
            cursor.execute("ALTER TABLE scans ADD COLUMN skipped_items TEXT;")
        conn.commit()

def create_scan(root_path: str, db_path: str = DB_FILE) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO scans (root_path, status) VALUES (?, 'in_progress')", (root_path,))
        conn.commit()
        return cursor.lastrowid

def insert_files_batch(file_records: List[Dict[str, Any]], db_path: str = DB_FILE) -> None:
    query = """
        INSERT INTO files (scan_id, path, name, ext, category, size, mtime, sha256)
        VALUES (:scan_id, :path, :name, :ext, :category, :size, :mtime, :sha256)
        ON CONFLICT(path) DO UPDATE SET
            scan_id = excluded.scan_id, name = excluded.name, ext = excluded.ext,
            category = excluded.category, size = excluded.size, mtime = excluded.mtime,
            sha256 = CASE WHEN files.size = excluded.size AND files.mtime = excluded.mtime THEN files.sha256 ELSE NULL END;
    """
    with get_connection(db_path) as conn:
        conn.executemany(query, file_records)
        conn.commit()

def update_scan_status(
    scan_id: int, 
    status: str, 
    total_scanned: int, 
    error_log: Optional[str] = None, 
    skipped_items: Optional[str] = None,
    db_path: str = DB_FILE
) -> None:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scans SET status = ?, total_scanned = ?, error_log = ?, skipped_items = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, total_scanned, error_log, skipped_items, scan_id))
        conn.commit()

def update_file_hash(file_id: int, sha256_hash: str, db_path: str = DB_FILE) -> None:
    """Updates the SHA-256 hash for a specific file record."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET sha256 = ? WHERE id = ?", (sha256_hash, file_id))
        conn.commit()