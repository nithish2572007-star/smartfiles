# Smart Personal File Management System

A high-performance local Flask web application that scans directories, sorts files by type, searches by name/keyword, finds exact duplicates using SHA-256 hashing, and reports storage usage.

## 🚀 Features

- **Managed Scanner:** Fast local directory traversal using `os.scandir`. Now features a **Bounded Thread Pool** to prevent system lag and **Batch Database Inserts** for maximum throughput.
- **Categorizer:** Automatically groups files into Documents, Images, Video, Audio, Code, Archives, and Others.
- **Advanced Search:** Filter files by name, keyword, category, and size with instant results.
- **Duplicate Detection:** Identifies exact duplicates by grouping by size and confirming with block-based SHA-256 hashing.
- **Advisory Cleanup:** Safely moves selected duplicates to the system recycle bin using `send2trash`.
- **Scan Management:** Ability to terminate active scans in real-time and track queued vs running scans.
- **Auto-Shutdown:** Automatically shuts down the server after a period of inactivity to save local resources.

## 🛠️ Technical Optimizations

This project is optimized for local machine performance:
- **Concurrency Control:** Uses a `ThreadPoolExecutor` to limit concurrent disk I/O and prevent "disk thrashing."
- **DB Performance:** Implemented **SQLite WAL (Write-Ahead Logging)** mode to allow simultaneous read and write operations without UI freezing.
- **Resource Safety:** Implemented capped error tracking to prevent memory exhaustion (OOM) during large-scale system scans.
- **Batching:** Files are committed to the database in batches of 1,000 to minimize disk sync overhead.

## 📋 Prerequisites

Python 3.12 or higher must be installed on your system. Download it from [python.org](https://www.python.org/downloads/).

## ⚙️ Setup & Installation

You can install this project using `uv` (recommended) or standard `pip`.

### Option 1: Using uv (Recommended)
This project uses `uv` for lightning-fast dependency management.

1. **Install uv:**
   - **macOS/Linux:**
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - **Windows:**
     ```powershell
     powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
     ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/nithish2572007-star/smartfiles.git
   cd smartfiles
   ```

3. **Install dependencies:**
   ```bash
   uv sync
   ```

4. **Run the application:**
   ```bash
   uv run python app.py
   ```

### Option 2: Using pip
1. **Clone the repository:**
   ```bash
   git clone https://github.com/nithish2572007-star/smartfiles.git
   cd smartfiles
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

## 🌐 Access the Dashboard
Open your browser and navigate to `http://127.0.0.1:5000`

## 📂 Project Structure
- `app.py`: Flask application entry point, API routes, and managed thread pool.
- `scanner.py`: Directory traversal logic with batching and memory safety.
- `categorizer.py`: File type classification logic.
- `db.py`: SQLite database management with WAL mode optimization.
- `duplicates.py`: SHA-256 based duplicate detection.
- `search.py`: File filtering and search implementation.
- `stats.py`: Storage and category statistics.
- `templates/`: Jinja2 HTML templates for the modern UI.
- `static/`: CSS and JavaScript assets for the dashboard.
