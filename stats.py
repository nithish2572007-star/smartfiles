from typing import Dict, Any, List
from db import get_connection

def get_storage_stats(scan_id: int, top_n: int = 10, db_path: str = "smartfiles.db") -> Dict[str, Any]:
    """
    Calculates total files and size, per-category breakdown, top N largest files,
    and total duplicate waste.
    """
    stats = {
        "total_files": 0,
        "total_size": 0,
        "categories": {},
        "largest_files": [],
        "duplicate_waste": 0
    }

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Total files and size[cite: 3]
        cursor.execute(
            "SELECT COUNT(id) as total_files, SUM(size) as total_size FROM files WHERE scan_id = ?", 
            (scan_id,)
        )
        totals = cursor.fetchone()
        if totals and totals["total_files"]:
            stats["total_files"] = totals["total_files"]
            stats["total_size"] = totals["total_size"] or 0

        # Per-category breakdown[cite: 3]
        cursor.execute(
            "SELECT category, COUNT(id) as count, SUM(size) as size FROM files WHERE scan_id = ? GROUP BY category", 
            (scan_id,)
        )
        for row in cursor.fetchall():
            stats["categories"][row["category"]] = {
                "count": row["count"],
                "size": row["size"] or 0
            }

        # Top N largest files[cite: 3]
        cursor.execute(
            "SELECT name, path, size, category FROM files WHERE scan_id = ? ORDER BY size DESC LIMIT ?", 
            (scan_id, top_n)
        )
        stats["largest_files"] = [dict(row) for row in cursor.fetchall()]

        # Total duplicate waste[cite: 3]
        cursor.execute("""
            SELECT SUM((hash_count - 1) * size) as duplicate_waste
            FROM (
                SELECT size, COUNT(id) as hash_count
                FROM files
                WHERE scan_id = ? AND sha256 IS NOT NULL
                GROUP BY sha256
                HAVING COUNT(id) > 1
            )
        """, (scan_id,))
        waste_row = cursor.fetchone()
        if waste_row and waste_row["duplicate_waste"]:
            stats["duplicate_waste"] = waste_row["duplicate_waste"]

    return stats