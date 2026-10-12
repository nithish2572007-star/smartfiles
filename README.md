# Smart Personal File Management System

A local Flask web application that scans directories, sorts files by type, searches by name/keyword, finds exact duplicates using SHA-256 hashing, and reports storage usage. 

## Features
* **Scanner:** Fast local directory traversal with `os.scandir`, skipping unreadable files and symlinks.
* **Categorizer:** Automatically groups files into Documents, Images, Video, Audio, Code, Archives, and Others.
* **Search:** Filter files by name, keyword, category, size, and date.
* **Duplicate Detection:** Identifies exact duplicates by grouping by size and confirming with block-based SHA-256 hashing.
* **Advisory Cleanup:** Safely moves selected duplicates to the system recycle bin using `send2trash`.

## Setup & Installation

This project uses `uv` for lightning-fast dependency management.

1. Clone the repository:
   ```bash
   git clone [https://github.com/nithish2572007-star/smartfiles.git](https://github.com/nithish2572007-star/smartfiles.git)
   cd smartfiles