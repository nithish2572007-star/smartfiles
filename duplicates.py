import hashlib
from collections import defaultdict
from typing import List, Dict, Any
from db import get_connection, update_file_hash

def hash_file(file_path: str, block_size: int = 65536) -> str:
    """
    Computes the SHA-256 hash of a file by reading it in 64 KB blocks[cite: 2].
    Returns None if the file cannot be read.
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(block_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (OSError, PermissionError):
        return None

def find_duplicates(scan_id: int, db_path: str = "smartfiles.db") -> List[Dict[str, Any]]:
    """
    Finds exact file duplicates by first grouping by size, then confirming with SHA-256 hashes[cite: 2].
    Calculates wasted storage space per duplicate group[cite: 2].
    """
    duplicate_groups = []
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1 & 2. Exclude zero-byte files, group by size, and find sizes with > 1 file[cite: 2]
        cursor.execute("""
            SELECT size FROM files 
            WHERE scan_id = ? AND size > 0 
            GROUP BY size 
            HAVING COUNT(id) > 1
        """, (scan_id,))
        
        sizes_with_dupes = [row["size"] for row in cursor.fetchall()]

        for size in sizes_with_dupes:
            cursor.execute("""
                SELECT id, path, name, sha256 FROM files
                WHERE scan_id = ? AND size = ?
            """, (scan_id, size))
            
            candidates = cursor.fetchall()
            hash_buckets = defaultdict(list)
            
            # 3 & 4. Hash the candidates and group by hash[cite: 2]
            for file_record in candidates:
                file_id = file_record["id"]
                path = file_record["path"]
                stored_hash = file_record["sha256"]
                
                # 6. Skip hashing if previously stored and unchanged
                current_hash = stored_hash
                if not current_hash:
                    current_hash = hash_file(path)
                    if current_hash:
                        update_file_hash(file_id, current_hash, db_path)
                
                if current_hash:
                    hash_buckets[current_hash].append(dict(file_record))
            
            # 5. Compute wasted space per group as (n-1) * s[cite: 2]
            for file_hash, group in hash_buckets.items():
                if len(group) > 1:
                    wasted_space = (len(group) - 1) * size
                    duplicate_groups.append({
                        "hash": file_hash,
                        "size": size,
                        "count": len(group),
                        "wasted_space": wasted_space,
                        "files": group
                    })
                    
    return duplicate_groups