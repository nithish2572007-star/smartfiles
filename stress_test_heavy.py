import requests
import time
import concurrent.futures
import json

BASE_URL = "http://127.0.0.1:5000"

def start_scan():
    try:
        # Use the same directory to cause DB contention
        res = requests.post(f"{BASE_URL}/api/scan", json={"paths": ["/home/nithish/Projects/smartfiles/stress_test_data"]}, timeout=5)
        return res.status_code, res.json()
    except Exception as e:
        return 500, str(e)

def search_files():
    try:
        res = requests.get(f"{BASE_URL}/api/search", params={"keyword": "test"}, timeout=5)
        return res.status_code, res.json()
    except Exception as e:
        return 500, str(e)

def run_test(num_requests, concurrent_users):
    print(f"Testing with {concurrent_users} concurrent users, {num_requests} total requests...")
    start_time = time.time()
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        for i in range(num_requests):
            # Heavily weight towards starting scans to stress the DB and threads
            if i % 2 == 0:
                futures.append(executor.submit(start_scan))
            else:
                futures.append(executor.submit(search_files))
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    end_time = time.time()
    duration = end_time - start_time
    
    successes = [r for r in results if r[0] == 200]
    errors = [r for r in results if r[0] != 200]
    
    print(f"Successful: {len(successes)}, Errors: {len(errors)}, Total Time: {duration:.2f}s")
    if errors:
        print(f"Sample Error: {errors[0]}")

if __name__ == "__main__":
    # Rapidly increase concurrency to find the breaking point
    for users in [10, 50, 100, 200, 500]:
        run_test(200, users)
        print("-" * 30)
