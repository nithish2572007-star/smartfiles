import os
import time
import signal
import shutil
import atexit
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template
from send2trash import send2trash

# Import our custom modules
from db import init_db, create_scan, get_connection, update_scan_status
from scanner import run_scan, stop_scan_flag
from search import search_files
from duplicates import find_duplicates
from stats import get_storage_stats

app = Flask(__name__)

# Ensure the database is initialized when the app starts
init_db()

# Thread pool for managed scan execution
MAX_SCAN_WORKERS = int(os.environ.get("MAX_SCAN_WORKERS", 4))
scan_executor = ThreadPoolExecutor(max_workers=MAX_SCAN_WORKERS, thread_name_prefix="scan_worker")

# Inactivity timeout configuration (default: 5 minutes / 300 seconds)
INACTIVITY_TIMEOUT_SECONDS = int(os.environ.get("INACTIVITY_TIMEOUT_SECONDS", 300))
last_activity_time = time.time()

# Scan tracking state: queued vs running
scans_lock = threading.Lock()
queued_scans_count = 0
running_scans_count = 0

def cleanup_executor():
    """Signals scanner to stop and cleanly shuts down the scan worker pool."""
    import scanner
    scanner.stop_scan_flag = True
    try:
        scan_executor.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass

atexit.register(cleanup_executor)

@app.before_request
def update_activity():
    """Updates the last activity timestamp on user requests, excluding passive status polls if no scan is active."""
    global last_activity_time
    last_activity_time = time.time()

def inactivity_watcher():
    """Monitors inactivity and shuts down the process after INACTIVITY_TIMEOUT_SECONDS of idle time."""
    while True:
        time.sleep(5)
        with scans_lock:
            busy = (queued_scans_count + running_scans_count) > 0
        
        idle_duration = time.time() - last_activity_time
        if idle_duration >= INACTIVITY_TIMEOUT_SECONDS and not busy:
            print(f"\n[SmartFiles] Inactive for {INACTIVITY_TIMEOUT_SECONDS}s ({INACTIVITY_TIMEOUT_SECONDS // 60} min). Auto-shutting down...")
            cleanup_executor()
            try:
                os.kill(os.getpid(), signal.SIGINT)
            except Exception:
                os._exit(0)
            break

# Start the background inactivity watcher as a daemon thread
watcher_thread = threading.Thread(target=inactivity_watcher, daemon=True)
watcher_thread.start()

def scan_background(paths: list, scan_id: int):
    """
    Executes the scan within a managed ThreadPoolExecutor worker.
    Tracks queued vs running scans and encloses execution in an error boundary.
    """
    global queued_scans_count, running_scans_count, last_activity_time
    with scans_lock:
        queued_scans_count = max(0, queued_scans_count - 1)
        running_scans_count += 1
    try:
        run_scan(paths, scan_id)
    except Exception as exc:
        logging.exception(f"Unhandled scan failure for scan_id={scan_id}: {exc}")
        try:
            update_scan_status(
                scan_id, 'failed', 0, 
                error_log=f"Worker exception: {str(exc)}"
            )
        except Exception:
            pass
    finally:
        with scans_lock:
            running_scans_count = max(0, running_scans_count - 1)
        last_activity_time = time.time()

@app.route('/api/scan', methods=['POST'])
def start_scan():
    """Endpoint: POST /scan. Initializes and queues a background scan via ThreadPoolExecutor."""
    global queued_scans_count
    data = request.get_json() or {}
    paths = data.get('paths')
    if not paths and data.get('path'):
        paths = [data.get('path')]
        
    if not paths or not isinstance(paths, list):
        return jsonify({'error': 'Please provide one or more valid directory paths'}), 400
        
    cleaned_paths = [p.strip() for p in paths if isinstance(p, str) and p.strip()]
    if not cleaned_paths:
        return jsonify({'error': 'No valid directory paths provided'}), 400
        
    # Represent combined root paths as comma-separated in scans record
    root_path_str = ", ".join(cleaned_paths)
    scan_id = create_scan(root_path_str)
    
    with scans_lock:
        queued_scans_count += 1
        is_queued = running_scans_count >= MAX_SCAN_WORKERS
        current_queued = queued_scans_count
        current_running = running_scans_count

    # Submit task to the bounded ThreadPoolExecutor
    scan_executor.submit(scan_background, cleaned_paths, scan_id)
    
    message = 'Scan queued' if is_queued else 'Scan started'
    return jsonify({
        'scan_id': scan_id, 
        'message': message,
        'queued_scans': current_queued,
        'running_scans': current_running
    })

@app.route('/api/scan/terminate', methods=['POST'])
def terminate_scan():
    """Endpoint: POST /scan/terminate. Stops the currently running scan."""
    import scanner
    scanner.stop_scan_flag = True
    return jsonify({'message': 'Termination signal sent to scanner'})

@app.route('/api/scans', methods=['GET'])
def list_scans():
    """Endpoint: GET /api/scans. Retrieves recent scans for quick selection."""
    with get_connection() as conn:
        scans = conn.execute(
            "SELECT id, root_path, started_at, completed_at, status, total_scanned FROM scans ORDER BY id DESC LIMIT 30"
        ).fetchall()
        return jsonify([dict(s) for s in scans])

@app.route('/api/scan/<int:scan_id>/status', methods=['GET'])
def scan_status(scan_id):
    """Poll for progress and retrieve status and skipped items."""
    with get_connection() as conn:
        scan = conn.execute(
            "SELECT status, total_scanned, error_log, skipped_items FROM scans WHERE id = ?", 
            (scan_id,)
        ).fetchone()
        
        if scan:
            res = dict(scan)
            if res.get('skipped_items'):
                try:
                    import json
                    res['skipped_items'] = json.loads(res['skipped_items'])
                except Exception:
                    pass
            else:
                res['skipped_items'] = []
            return jsonify(res)
        return jsonify({'error': 'Scan not found'}), 404

@app.route('/api/move', methods=['POST'])
def move_file():
    """
    Moves/transfers a file to a new target directory or path.
    Requires explicit user action from the frontend.
    Updates or clears the file record in the database accordingly.
    """
    data = request.get_json() or {}
    source = data.get('source')
    destination = data.get('destination')
    
    if not source or not os.path.exists(source):
        return jsonify({'error': 'Source file not found'}), 404
    if not destination:
        return jsonify({'error': 'Destination directory or path must be specified'}), 400
        
    try:
        # If destination is an existing directory, move file into it
        if os.path.isdir(destination):
            dest_file_path = os.path.join(destination, os.path.basename(source))
        else:
            # If destination parent dir exists, it's a target filepath
            parent_dir = os.path.dirname(destination)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            dest_file_path = destination

        if os.path.exists(dest_file_path) and os.path.abspath(dest_file_path) != os.path.abspath(source):
            return jsonify({'error': f'Destination already exists: {dest_file_path}'}), 400

        shutil.move(source, dest_file_path)

        # Update the database record if present
        with get_connection() as conn:
            conn.execute("UPDATE files SET path = ?, name = ? WHERE path = ?", 
                         (dest_file_path, os.path.basename(dest_file_path), source))
            conn.commit()

        return jsonify({
            'message': f'Successfully moved {os.path.basename(source)} to {dest_file_path}',
            'new_path': dest_file_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/<int:scan_id>', methods=['GET'])
def stats(scan_id):
    """Endpoint: GET /stats[cite: 3]. Returns JSON storage statistics[cite: 3]."""
    return jsonify(get_storage_stats(scan_id))

@app.route('/api/duplicates/<int:scan_id>', methods=['GET'])
def duplicates(scan_id):
    """Endpoint: GET /duplicates[cite: 3]."""
    return jsonify(find_duplicates(scan_id))

@app.route('/api/search', methods=['GET'])
def search():
    """Endpoint: GET /search[cite: 3]."""
    keyword = request.args.get('keyword')
    category = request.args.get('category')
    min_size = request.args.get('min_size', type=int)
    max_size = request.args.get('max_size', type=int)
    start_date = request.args.get('start_date', type=float)
    end_date = request.args.get('end_date', type=float)
    
    results = search_files(
        keyword=keyword, 
        category=category, 
        min_size=min_size, 
        max_size=max_size,
        start_date=start_date,
        end_date=end_date
    )
    return jsonify(results)

@app.route('/api/delete', methods=['POST'])
def delete_file():
    """
    Sends files to the recycle bin (send2trash), never a permanent delete[cite: 3].
    Requires explicit confirmation via the frontend[cite: 3].
    """
    data = request.get_json() or {}
    path = data.get('path')
    
    if not path or not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        send2trash(path)
        with get_connection() as conn:
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
            conn.commit()
        return jsonify({'message': f'Successfully moved {os.path.basename(path)} to recycle bin'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('index.html')

@app.route('/search')
def search_page():
    """Serves the search interface."""
    return render_template('search.html')

@app.route('/duplicates')
def duplicates_page():
    """Serves the duplicate review interface."""
    return render_template('duplicates.html')

if __name__ == '__main__':
    app.run(debug=True)