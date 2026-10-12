from typing import List, Dict, Any, Optional
from db import get_connection

def search_files(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    start_date: Optional[float] = None,
    end_date: Optional[float] = None,
    db_path: str = "smartfiles.db"
) -> List[Dict[str, Any]]:
    """
    Searches files by filename/keyword using SQL LIKE, and applies filters
    for category, size range, and modification date[cite: 2].
    """
    query_parts = ["SELECT * FROM files WHERE 1=1"]
    params = []

    if keyword:
        # SQL LIKE for filename and keyword search[cite: 2]
        query_parts.append("AND name LIKE ?")
        params.append(f"%{keyword}%")

    if category:
        # Filter for file type[cite: 2]
        query_parts.append("AND category = ?")
        params.append(category)

    if min_size is not None:
        # Filter for size range (minimum)[cite: 2]
        query_parts.append("AND size >= ?")
        params.append(min_size)

    if max_size is not None:
        # Filter for size range (maximum)[cite: 2]
        query_parts.append("AND size <= ?")
        params.append(max_size)

    if start_date is not None:
        # Filter for date (minimum modified time)[cite: 2]
        query_parts.append("AND mtime >= ?")
        params.append(start_date)

    if end_date is not None:
        # Filter for date (maximum modified time)[cite: 2]
        query_parts.append("AND mtime <= ?")
        params.append(end_date)

    sql_query = " ".join(query_parts)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_query, params)
        rows = cursor.fetchall()
        
    return [dict(row) for row in rows]