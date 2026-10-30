import os
import time
import json
import socket
import threading
import concurrent.futures

BASE_URL = "http://127.0.0.1:5000"
SCAN_PATH = [os.path.abspath("stress_test_data")]

# Flexible HTTP helpers: use requests if installed, otherwise urllib
try:
    import requests
    def http_post(url, json_data):
        return requests.post(url, json=json_data, timeout=15).status_code
    def http_get(url, params):
        return requests.get(url, params=params, timeout=15).status_code
except ImportError:
    import urllib.request
    import urllib.parse
    def http_post(url, json_data):
        data = json.dumps(json_data).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    def http_get(url, params):
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{qs}")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status

def start_scan():
    try:
        return http_post(f"{BASE_URL}/api/scan", {"paths": SCAN_PATH})
    except Exception as e:
        return f"Error: {e}"

def search_files():
    try:
        return http_get(f"{BASE_URL}/api/search", {"keyword": "test"})
    except Exception as e:
        return f"Error: {e}"

def test_hammer():
    print("\n--- Running 'The Hammer' Test (Rapid Scan Starts) ---")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(start_scan) for _ in range(50)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    
    success = results.count(200)
    print(f"Started 50 scans. Success: {success}, Failures: {len(results)-success}")
    assert success == 50, f"Expected 50 successful scans, got {success}"

def test_conflict():
    print("\n--- Running 'Read-Write Conflict' Test (Scan vs Search) ---")
    # Start one heavy scan in background
    threading.Thread(target=start_scan, daemon=True).start()
    time.sleep(0.5)  # Let worker queue/start
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(search_files) for _ in range(200)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
            
    success = results.count(200)
    print(f"Performed 200 searches during active scan. Success: {success}, Failures: {len(results)-success}")
    assert success == 200, f"Expected 200 successful searches, got {success}"

def is_server_listening(host="127.0.0.1", port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

if __name__ == "__main__":
    server = None
    if not is_server_listening():
        print("Starting local test server on 127.0.0.1:5000...")
        from werkzeug.serving import make_server
        from app import app
        
        class ServerThread(threading.Thread):
            def __init__(self, flask_app):
                super().__init__(daemon=True)
                self.server = make_server('127.0.0.1', 5000, flask_app)

            def run(self):
                self.server.serve_forever()

            def shutdown(self):
                self.server.shutdown()

        server = ServerThread(app)
        server.start()
        time.sleep(1)

    try:
        test_hammer()
        test_conflict()
        print("\nAll stress tests passed successfully without locking or crashes!")
    finally:
        if server:
            server.shutdown()
