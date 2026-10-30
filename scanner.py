import os
import json
import logging
from typing import List, Dict, Any, Tuple, Union, Optional
from db import insert_files_batch, update_scan_status
from categorizer import get_category

logger = logging.getLogger("smartfiles.scanner")
if not logger.handlers:
    _stream_h = logging.StreamHandler()
    _stream_h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(_stream_h)
    try:
        _file_h = logging.FileHandler('scan_errors.log', encoding='utf-8')
        _file_h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(_file_h)
    except (OSError, PermissionError):
        pass
    logger.setLevel(logging.ERROR)

BATCH_SIZE = 1000

# Global flag to stop scanning
stop_scan_flag = False

# Known system folders and pseudo-filesystems across Linux, macOS, and Windows
SYSTEM_BASENAMES = {
    'proc', 'sys', 'dev', 'run', 'var/run', 'var/lock',
    'windows', 'pagefile.sys', 'hiberfil.sys',
    'system volume information', '$recycle.bin', '.trash', '.trashes'
}
SYSTEM_EXACT_PATHS = {
    '/proc', '/sys', '/dev', '/run', '/var/run', '/var/lock',
    'c:\\windows', 'c:\\pagefile.sys', 'c:\\hiberfil.sys'
}

def is_system_directory(path: str) -> bool:
    """Checks whether the directory is a known system directory or virtual filesystem."""
    normalized = os.path.abspath(path).lower()
    base = os.path.basename(normalized)
    if base in SYSTEM_BASENAMES or normalized in SYSTEM_EXACT_PATHS:
        return True
    for prefix in ('/proc', '/sys', '/dev', '/run'):
        if normalized == prefix or normalized.startswith(prefix + '/'):
            return True
    return False

def run_scan(
    root_paths: Union[str, List[str]], 
    scan_id: int, 
    db_path: str = "smartfiles.db"
) -> Tuple[int, int, List[Dict[str, str]]]:
    """
    Scans one or more directories, ignoring and reporting system folders and unreadable files.
    Returns (total_scanned, error_count, skipped_items).
    """
    global stop_scan_flag
    stop_scan_flag = False
    batch: List[Dict[str, Any]] = []
    total_scanned = 0
    error_count = 0
    skipped_items: List[Dict[str, str]] = []
    MAX_SKIPPED_TRACKED = 1000  # Prevent RAM exhaustion

    if isinstance(root_paths, str):
        dirs_to_scan = [p.strip() for p in root_paths.split(',') if p.strip()]
    else:
        dirs_to_scan = list(root_paths)

    # Initial validation of provided directories
    active_dirs = []
    for d in dirs_to_scan:
        abs_d = os.path.abspath(d)
        if is_system_directory(abs_d):
            if len(skipped_items) < MAX_SKIPPED_TRACKED:
                skipped_items.append({"path": abs_d, "reason": "System folder ignored"})
            continue
        if not os.path.isdir(abs_d):
            if len(skipped_items) < MAX_SKIPPED_TRACKED:
                skipped_items.append({"path": abs_d, "reason": "Directory does not exist or inaccessible"})
            continue
        active_dirs.append(abs_d)

    dirs_to_scan = active_dirs

    try:
        while dirs_to_scan:
            if stop_scan_flag:
                break

            current_dir = dirs_to_scan.pop()
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if stop_scan_flag:
                            break
                        if entry.is_symlink():
                            continue
                        if entry.is_dir():
                            if is_system_directory(entry.path):
                                if len(skipped_items) < MAX_SKIPPED_TRACKED:
                                    skipped_items.append({"path": entry.path, "reason": "System folder ignored"})
                                continue
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
                                if len(skipped_items) < MAX_SKIPPED_TRACKED:
                                    skipped_items.append({"path": entry.path, "reason": f"Unreadable file: {str(e)}"})
                                logger.error(f"File read error at {entry.path}: {e}")
            except (OSError, PermissionError) as e:
                error_count += 1
                if len(skipped_items) < MAX_SKIPPED_TRACKED:
                    skipped_items.append({"path": current_dir, "reason": f"Inaccessible directory: {str(e)}"})
                logger.error(f"Directory access error at {current_dir}: {e}")

        if stop_scan_flag:
            if batch:
                try:
                    insert_files_batch(batch, db_path=db_path)
                    batch.clear()
                except Exception as e:
                    logger.error(f"Error flushing final batch on cancel: {e}")
            skipped_json = json.dumps(skipped_items) if skipped_items else None
            update_scan_status(
                scan_id, 'cancelled', total_scanned, 
                "Scan terminated by user.", skipped_items=skipped_json, db_path=db_path
            )
            return total_scanned, error_count, skipped_items

        if batch:
            insert_files_batch(batch, db_path=db_path)
            batch.clear()
            
        error_log_summary = f"Encountered {error_count} errors." if error_count > 0 else None
        skipped_json = json.dumps(skipped_items) if skipped_items else None
        update_scan_status(scan_id, 'completed', total_scanned, error_log_summary, skipped_items=skipped_json, db_path=db_path)
        return total_scanned, error_count, skipped_items
    except Exception as exc:
        logger.exception(f"Unhandled scan error in scan_id {scan_id}: {exc}")
        if batch:
            try:
                insert_files_batch(batch, db_path=db_path)
                batch.clear()
            except Exception:
                pass
        skipped_json = json.dumps(skipped_items) if skipped_items else None
        update_scan_status(
            scan_id, 'failed', total_scanned,
            f"Fatal error during scan: {str(exc)}", skipped_items=skipped_json, db_path=db_path
        )
        raise
