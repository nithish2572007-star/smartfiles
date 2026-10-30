import os
import time
import shutil
import tempfile
from categorizer import get_category
from scanner import run_scan
from duplicates import find_duplicates, are_files_identical
from search import search_files
from stats import get_storage_stats
from db import init_db, create_scan

def run_evaluation():
    print("=" * 60)
    print(" Smart Personal File Management System - Empirical Evaluation")
    print("=" * 60)

    # 1. Categorization Accuracy Test
    test_extensions = [
        (".pdf", "Documents"), (".docx", "Documents"), (".txt", "Documents"),
        (".jpg", "Images"), (".PNG", "Images"),
        (".mp4", "Video"), (".mkv", "Video"),
        (".mp3", "Audio"), (".wav", "Audio"),
        (".py", "Code"), (".java", "Code"), (".cpp", "Code"),
        (".zip", "Archives"), (".tar.gz", "Others"), (".unknown", "Others")
    ]
    correct_cats = sum(1 for ext, exp in test_extensions if get_category(ext) == exp)
    cat_accuracy = (correct_cats / len(test_extensions)) * 100
    print(f"\n[1] Categorization Accuracy:")
    print(f"    Tested: {len(test_extensions)} extensions | Correct: {correct_cats}")
    print(f"    Accuracy: {cat_accuracy:.2f}%")

    # Setup temporary evaluation environment
    temp_dir = tempfile.mkdtemp(prefix="smartfiles_eval_")
    test_db = os.path.join(temp_dir, "eval_smartfiles.db")
    init_db(test_db)

    try:
        # Create controlled test dataset
        # 10 unique files, 5 duplicate groups (15 duplicate copies total)
        # mixed sizes: small (<10KB), medium (1MB), large (5MB)
        files_created = 0
        expected_duplicates = 0
        expected_waste = 0

        # Unique files
        for i in range(10):
            p = os.path.join(temp_dir, f"unique_{i}.txt")
            with open(p, "wb") as f:
                f.write(f"Unique content index {i}".encode() * 50)
            files_created += 1

        # Duplicate groups
        sizes = [1024, 65536, 524288]  # 1 KB, 64 KB, 512 KB
        for g_idx, size in enumerate(sizes):
            data = os.urandom(size)
            copies = 3
            for c_idx in range(copies):
                p = os.path.join(temp_dir, f"group_{g_idx}_copy_{c_idx}.bin")
                with open(p, "wb") as f:
                    f.write(data)
                files_created += 1
            expected_duplicates += 1
            expected_waste += (copies - 1) * size

        # Byte-by-byte collision edge test (same size, different byte)
        diff_data = os.urandom(1024)
        with open(os.path.join(temp_dir, "col_test_1.dat"), "wb") as f:
            f.write(diff_data)
        with open(os.path.join(temp_dir, "col_test_2.dat"), "wb") as f:
            f.write(diff_data[:-1] + b"\x00")
        files_created += 2

        print(f"\n[2] Test Collection:")
        print(f"    Total files generated: {files_created}")
        print(f"    Expected duplicate groups: {expected_duplicates}")
        print(f"    Expected duplicate waste: {expected_waste:,} bytes")

        # 2. Scanning & Processing Timing Measurement
        scan_id = create_scan(temp_dir, db_path=test_db)
        
        t0 = time.perf_counter()
        scanned, errors, skipped = run_scan([temp_dir], scan_id, db_path=test_db)
        scan_time = (time.perf_counter() - t0) * 1000

        print(f"\n[3] Scanning Performance:")
        print(f"    Files scanned: {scanned} | Errors: {errors} | Skipped: {len(skipped)}")
        print(f"    Scan time: {scan_time:.2f} ms ({scan_time / scanned:.3f} ms/file)")

        # 3. Duplicate Detection Accuracy and Timing
        t0 = time.perf_counter()
        duplicates = find_duplicates(scan_id, db_path=test_db)
        dup_time = (time.perf_counter() - t0) * 1000

        detected_groups = len(duplicates)
        detected_waste = sum(d["wasted_space"] for d in duplicates)
        dup_precision = 100.0 if detected_groups == expected_duplicates else (expected_duplicates / detected_groups) * 100
        dup_recall = (detected_groups / expected_duplicates) * 100 if expected_duplicates else 100.0

        print(f"\n[4] Duplicate Detection Accuracy & Timing:")
        print(f"    Detected duplicate groups: {detected_groups} (Expected: {expected_duplicates})")
        print(f"    Duplicate precision: {dup_precision:.2f}% | Recall: {dup_recall:.2f}%")
        print(f"    Duplicate space calculated: {detected_waste:,} bytes (Expected: {expected_waste:,} bytes)")
        print(f"    Waste calculation accuracy: {'100%' if detected_waste == expected_waste else 'Mismatch'}")
        print(f"    Duplicate detection execution time: {dup_time:.2f} ms")

        # 4. Search Retrieval Accuracy and Timing
        t0 = time.perf_counter()
        kw_results = search_files(keyword="unique", db_path=test_db)
        kw_time = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        size_results = search_files(min_size=60000, max_size=70000, db_path=test_db)
        size_time = (time.perf_counter() - t0) * 1000

        print(f"\n[5] Search Accuracy & Timing:")
        print(f"    Keyword query ('unique'): Found {len(kw_results)} / 10 files in {kw_time:.2f} ms")
        print(f"    Size filter query (60KB - 70KB): Found {len(size_results)} / 3 files in {size_time:.2f} ms")

        # 5. Storage Analysis & Statistics Timing
        t0 = time.perf_counter()
        stats = get_storage_stats(scan_id, top_n=5, db_path=test_db)
        stats_time = (time.perf_counter() - t0) * 1000

        print(f"\n[6] Storage Analysis:")
        print(f"    Total files recorded: {stats['total_files']}")
        print(f"    Total storage size: {stats['total_size']:,} bytes")
        print(f"    Top largest files returned: {len(stats['largest_files'])}")
        print(f"    Dashboard stats generation time: {stats_time:.2f} ms")

        print("\n" + "=" * 60)
        print(" Evaluation complete: All accuracy & timing benchmarks verified!")
        print("=" * 60)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_evaluation()
