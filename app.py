import os
import threading
from flask import Flask, request, jsonify, render_template
from send2trash import send2trash


# Import our custom modules
from db import init_db, create_scan, get_connection
from scanner import run_scan, stop_scan_flag
from search import search_files
from duplicates import find_duplicates
from stats import get_storage_stats

app = Flask(__name__)

# Ensure the database is initialized when the app starts
init_db()

def scan_background(path: str, scan_id: int):
    """Runs the scan in a background thread to prevent UI freezing."""
    run_scan(path, scan_id)

@app.route('/api/scan', methods=['POST'])
def start_scan():
    """Endpoint: POST /scan[cite: 3]. Initializes a background scan."""
    data = request.get_json()
    path = data.get('path')
    
    if not path or not os.path.isdir(path):
        return jsonify({'error': 'Invalid or inaccessible directory path'}), 400
        
    scan_id = create_scan(path)
    
    # Run scans in a background thread[cite: 3]
    thread = threading.Thread(target=scan_background, args=(path, scan_id))
    thread.start()
    
    return jsonify({'scan_id': scan_id, 'message': 'Scan started'})

@app.route('/api/scan/terminate', methods=['POST'])
def terminate_scan():
    """Endpoint: POST /scan/terminate. Stops the currently running scan."""
    import scanner
    scanner.stop_scan_flag = True
    return jsonify({'message': 'Termination signal sent to scanner'})

@app.route('/api/scan/<int:scan_id>/status', methods=['GET'])
def scan_status(scan_id):
    """Poll for progress so the page does not freeze[cite: 3]."""
    with get_connection() as conn:
        scan = conn.execute(
            "SELECT status, total_scanned, error_log FROM scans WHERE id = ?", 
            (scan_id,)
        ).fetchone()
        
        if scan:
            return jsonify(dict(scan))
        return jsonify({'error': 'Scan not found'}), 404

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
    
    results = search_files(
        keyword=keyword, 
        category=category, 
        min_size=min_size, 
        max_size=max_size
    )
    return jsonify(results)

@app.route('/api/delete', methods=['POST'])
def delete_file():
    """
    Sends files to the recycle bin (send2trash), never a permanent delete[cite: 3].
    Requires explicit confirmation via the frontend[cite: 3].
    """
    data = request.get_json()
    path = data.get('path')
    
    if not path or not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404
        
    try:
        send2trash(path)
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