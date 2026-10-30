import time
import json
import concurrent.futures

BASE_URL = "http://127.0.0.1:5000"

try:
    import requests
    def http_post(url, json_data):
        res = requests.post(url, json=json_data, timeout=10)
        return res.status_code, res.json()
    def http_get(url, params):
        res = requests.get(url, params=params, timeout=10)
        return res.status_code, res.json()
except ImportError:
    import urllib.request
    import urllib.parse
    def http_post(url, json_data):
        data = json.dumps(json_data).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    def http_get(url, params):
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{qs}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

def start_scan():
    try:
        return http_post(f"{BASE_URL}/api/scan", {"paths": ["/home/nithish/Projects/smartfiles/stress_test_data"]})
    except Exception as e:
        return 500, str(e)

def search_files():
    try:
        return http_get(f"{BASE_URL}/api/search", {"keyword": "test"})
    except Exception as e:
        return 500, str(e)

def run_test(num_requests, concurrent_users):
    print(f"Starting stress test: {num_requests} requests, {concurrent_users} concurrent users")
    start_time = time.time()
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        # Mix of scan starts and search requests
        futures = []
        for i in range(num_requests):
            if i % 5 == 0: # Start a scan every 5th request
                futures.append(executor.submit(start_scan))
            else:
                futures.append(executor.submit(search_files))
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    end_time = time.time()
    duration = end_time - start_time
    
    successes = [r for r in results if r[0] == 200]
    errors = [r for r in results if r[0] != 200]
    
    print(f"\n--- Results ---")
    print(f"Total Requests: {num_requests}")
    print(f"Successful: {len(successes)}")
    print(f"Errors: {len(errors)}")
    print(f"Total Time: {duration:.2f}s")
    print(f"Avg Response Time: {duration/num_requests:.4f}s")
    if errors:
        print(f"Sample Error: {errors[0]}")

if __name__ == "__main__":
    # We'll start with a moderate load and increase it
    for users in [1, 10, 50]:
        run_test(100, users)
        print("-" * 30)
