# Smart Personal File Management System

A local Flask web application that scans directories, sorts files by type, searches by name/keyword, finds exact duplicates using SHA-256 hashing, and reports storage usage.

## Features
* **Scanner:** Fast local directory traversal with `os.scandir`, skipping unreadable files and symlinks.
* **Categorizer:** Automatically groups files into Documents, Images, Video, Audio, Code, Archives, and Others.
* **Search:** Filter files by name, keyword, category, and size.
* **Duplicate Detection:** Identifies exact duplicates by grouping by size and confirming with block-based SHA-256 hashing.
* **Advisory Cleanup:** Safely moves selected duplicates to the system recycle bin using `send2trash`.
* **Scan Management:** Ability to terminate active scans in real-time via the dashboard.

## Setup & Installation

This project uses `uv` for lightning-fast dependency management.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nithish2572007-star/smartfiles.git
   cd smartfiles
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the application:**
   ```bash
   uv run python app.py
   ```
   *Alternatively, using Flask CLI:*
   ```bash
   uv run flask run
   ```

4. **Access the Dashboard:**
   Open your browser and navigate to `http://127.0.0.1:5000`

## Project Structure
- `app.py`: Flask application entry point and API routes.
- `scanner.py`: Directory traversal and file scanning logic.
- `categorizer.py`: File type classification.
- `db.py`: SQLite database management.
- `duplicates.py`: SHA-256 based duplicate detection.
- `search.py`: File filtering and search implementation.
- `stats.py`: Storage and category statistics.
- `templates/`: Jinja2 HTML templates for the UI.
- `static/`: CSS and JavaScript assets.
