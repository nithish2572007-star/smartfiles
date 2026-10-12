import os
import logging
from typing import List, Dict, Any, Tuple
from db import insert_files_batch, update_scan_status
from categorizer import get_category

logging.basicConfig(filename='scan_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
BATCH_SIZE = 500

def run_scan(root_path: str, scan_id: int, db_path: str = "smartfiles.db") -> Tuple[int, int]:
    batch: List[Dict[str, Any]] = []
    total_scanned = 0
    error_count = 0
    dirs_to_scan = [root_path]

    while dirs_to_scan:
        current_dir = dirs_to_scan.pop()
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir():
                        dirs_to_scan.append(entry.path)
                    elif entry.is_file():
                        try:
                            stat = entry.stat()
                            name = entry.name
                            ext = os.path.splitext(name)[1].lower()
                            
                            batch.append({
                                "scan_id": scan_id, "path": entry.path, "name": name, "ext": ext,
                                "category": get_category(ext), "size": stat.st_size, "mtime": stat.st_mtime, "sha256": None
                            })
                            total_scanned += 1
                            
                            if len(batch) >= BATCH_SIZE:
                                insert_files_batch(batch, db_path=db_path)
                                batch.clear()
                        except (OSError, PermissionError) as e:
                            error_count += 1
                            logging.error(f"File read error at {entry.path}: {e}")
        except (OSError, PermissionError) as e:
            error_count += 1
            logging.error(f"Directory access error at {current_dir}: {e}")

    if batch:
        insert_files_batch(batch, db_path=db_path)
        
    error_log_summary = f"Encountered {error_count} errors." if error_count > 0 else None
    update_scan_status(scan_id, 'completed', total_scanned, error_log_summary, db_path=db_path)
    return total_scanned, error_count