import os
import pytest
from db import init_db, create_scan
from scanner import run_scan
from categorizer import get_category
from duplicates import find_duplicates

TEST_DB = "test_smartfiles.db"

@pytest.fixture
def test_collection(tmp_path):
    """
    Builds the test collection required for Phase 8: mixed file types, 
    renamed duplicates, empty files, and same-name files with different content[cite: 3].
    """
    # 1. Mixed file types
    doc_path = tmp_path / "report.pdf"
    doc_path.write_text("Fake PDF content")

    # 2. Empty file (zero bytes)
    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("")

    # 3. Renamed duplicates & duplicates in different folders
    dupe_dir = tmp_path / "subfolder"
    dupe_dir.mkdir()
    
    orig_file = tmp_path / "photo.jpg"
    orig_file.write_text("Image data 123")
    
    renamed_dupe = dupe_dir / "copy_photo.jpg"
    renamed_dupe.write_text("Image data 123")

    # 4. Same-name files with different content
    diff_file = dupe_dir / "report.pdf"
    diff_file.write_text("Completely different PDF content")

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
    """Metrics: Categorization accuracy[cite: 3]."""
    assert get_category(".pdf") == "Documents"
    assert get_category(".JPG") == "Images"
    assert get_category(".unknown") == "Others"

def test_scanner_and_duplicates(test_collection):
    """
    Metrics: Duplicate detection accuracy (Precision and recall against the known 
    duplicate set, with no false matches)[cite: 3].
    """
    scan_id = create_scan(str(test_collection), db_path=TEST_DB)
    total_scanned, errors = run_scan(str(test_collection), scan_id, db_path=TEST_DB)
    
    # We created 5 files total
    assert total_scanned == 5
    assert errors == 0

    duplicates = find_duplicates(scan_id, db_path=TEST_DB)
    
    # We should only find exactly 1 duplicate group (photo.jpg and copy_photo.jpg)
    assert len(duplicates) == 1
    
    dupe_group = duplicates[0]
    assert dupe_group["count"] == 2
    
    # Verify the empty file was skipped (would otherwise group with other empty files)
    file_names = [f["name"] for f in dupe_group["files"]]
    assert "photo.jpg" in file_names
    assert "copy_photo.jpg" in file_names
    assert "empty.txt" not in file_names