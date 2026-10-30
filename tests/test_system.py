import os
import time
import pytest
from db import init_db, create_scan, get_connection
from scanner import run_scan
from categorizer import get_category
from duplicates import find_duplicates, are_files_identical
from search import search_files
from stats import get_storage_stats

TEST_DB = "test_smartfiles.db"

@pytest.fixture
def test_collection(tmp_path):
    """
    Builds the test collection required for evaluation:
    - Mixed file types (PDF, JPG, TXT, PY, ZIP)
    - Known duplicates with identical content (photo.jpg, copy_photo.jpg, photo_sub.jpg)
    - Empty file (zero bytes)
    - Same-name files with different content
    - Files with varied sizes for range filtering
    """
    # 1. Documents
    doc_path = tmp_path / "report.pdf"
    doc_path.write_bytes(b"Fake PDF report content 1234567890")

    # 2. Empty file (zero bytes, should be excluded from duplicates)
    empty_path = tmp_path / "empty.txt"
    empty_path.write_bytes(b"")

    # 3. Code file
    code_path = tmp_path / "script.py"
    code_path.write_bytes(b"print('hello world')")

    # 4. Known duplicate group (3 files across folders with identical content)
    photo_content = b"Binary JPEG content " + (b"X" * 1024)
    orig_file = tmp_path / "photo.jpg"
    orig_file.write_bytes(photo_content)

    dupe_dir = tmp_path / "subfolder"
    dupe_dir.mkdir()
    
    renamed_dupe = dupe_dir / "copy_photo.jpg"
    renamed_dupe.write_bytes(photo_content)

    sub_dupe_dir = tmp_path / "another_folder"
    sub_dupe_dir.mkdir()
    third_dupe = sub_dupe_dir / "photo_duplicate.jpg"
    third_dupe.write_bytes(photo_content)

    # 5. Same-name file with different content
    diff_file = dupe_dir / "report.pdf"
    diff_file.write_bytes(b"Completely different PDF content with distinct length")

    return tmp_path

@pytest.fixture(autouse=True)
def setup_database():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_categorization_accuracy():
    """Metrics: Categorization accuracy across standard and case variations."""
    assert get_category(".pdf") == "Documents"
    assert get_category(".DOCX") == "Documents"
    assert get_category(".JPG") == "Images"
    assert get_category(".png") == "Images"
    assert get_category(".mp4") == "Video"
    assert get_category(".mp3") == "Audio"
    assert get_category(".py") == "Code"
    assert get_category(".zip") == "Archives"
    assert get_category(".unknown_ext") == "Others"

def test_byte_by_byte_verification(tmp_path):
    """Metrics: Byte-by-byte verification catches identical vs divergent content."""
    f1 = tmp_path / "f1.bin"
    f2 = tmp_path / "f2.bin"
    f3 = tmp_path / "f3.bin"

    f1.write_bytes(b"A" * 1000)
    f2.write_bytes(b"A" * 1000)
    f3.write_bytes(b"A" * 999 + b"B")

    assert are_files_identical(str(f1), str(f2)) is True
    assert are_files_identical(str(f1), str(f3)) is False

def test_scanner_and_duplicate_detection(test_collection):
    """
    Metrics: Duplicate file detection accuracy, empty file exclusion,
    and storage calculation accuracy ((n - 1) * s).
    """
    start_time = time.perf_counter()
    scan_id = create_scan(str(test_collection), db_path=TEST_DB)
    total_scanned, errors, skipped = run_scan([str(test_collection)], scan_id, db_path=TEST_DB)
    scan_duration = time.perf_counter() - start_time

    # We created 7 files total across directories
    assert total_scanned == 7
    assert errors == 0
    assert scan_duration < 2.0  # Fast scanning on standard machines

    start_dup_time = time.perf_counter()
    duplicates = find_duplicates(scan_id, db_path=TEST_DB)
    dup_duration = time.perf_counter() - start_dup_time

    # Should detect exactly 1 duplicate group with 3 files
    assert len(duplicates) == 1
    group = duplicates[0]
    assert group["count"] == 3
    
    file_names = {f["name"] for f in group["files"]}
    assert file_names == {"photo.jpg", "copy_photo.jpg", "photo_duplicate.jpg"}
    assert "empty.txt" not in file_names
    assert "report.pdf" not in file_names

    # Wasted space calculation: (3 - 1) * file_size
    expected_wasted = 2 * group["size"]
    assert group["wasted_space"] == expected_wasted
    assert dup_duration < 2.0

def test_search_accuracy_and_filters(test_collection):
    """
    Metrics: Searching accuracy by keyword, category, size range, and modification date.
    """
    scan_id = create_scan(str(test_collection), db_path=TEST_DB)
    run_scan([str(test_collection)], scan_id, db_path=TEST_DB)

    # 1. Search by keyword
    kw_results = search_files(keyword="report", db_path=TEST_DB)
    assert len(kw_results) == 2
    assert all("report" in r["name"] for r in kw_results)

    # 2. Search by category
    code_results = search_files(category="Code", db_path=TEST_DB)
    assert len(code_results) == 1
    assert code_results[0]["name"] == "script.py"

    # 3. Search by size filter (min_size and max_size)
    photo_size = (test_collection / "photo.jpg").stat().st_size
    sized_results = search_files(min_size=photo_size - 10, max_size=photo_size + 10, db_path=TEST_DB)
    assert len(sized_results) == 3
    assert all("photo" in r["name"] for r in sized_results)

    # 4. Search by date
    now = time.time()
    recent_results = search_files(start_date=now - 3600, end_date=now + 3600, db_path=TEST_DB)
    assert len(recent_results) == 7

def test_system_folder_skipping(tmp_path):
    """
    Metrics: System folders and unreadable files are skipped, logged, and reported.
    """
    # Create fake /proc style structure inside tmp_path
    proc_mock = tmp_path / "proc"
    proc_mock.mkdir()
    (proc_mock / "dummy.txt").write_text("test")

    regular_dir = tmp_path / "regular"
    regular_dir.mkdir()
    (regular_dir / "valid.txt").write_text("valid content")

    scan_id = create_scan(str(tmp_path), db_path=TEST_DB)
    total_scanned, errors, skipped = run_scan([str(tmp_path)], scan_id, db_path=TEST_DB)

    # valid.txt should be indexed, proc should be skipped
    assert total_scanned == 1
    assert any("proc" in item["path"].lower() for item in skipped)

def test_storage_dashboard_stats(test_collection):
    """
    Metrics: Storage calculation accuracy, largest files listing, and duplicate waste.
    """
    scan_id = create_scan(str(test_collection), db_path=TEST_DB)
    run_scan([str(test_collection)], scan_id, db_path=TEST_DB)
    find_duplicates(scan_id, db_path=TEST_DB)

    stats = get_storage_stats(scan_id, top_n=5, db_path=TEST_DB)
    assert stats["total_files"] == 7
    assert stats["total_size"] > 0
    assert len(stats["largest_files"]) <= 5
    # Largest file should be at the top
    assert stats["largest_files"][0]["size"] >= stats["largest_files"][-1]["size"]
    assert "Images" in stats["categories"]
    assert stats["categories"]["Images"]["count"] == 3
    assert stats["duplicate_waste"] > 0
