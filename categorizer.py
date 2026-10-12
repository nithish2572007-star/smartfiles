EXTENSION_MAP = {
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents", ".txt": "Documents", ".xls": "Documents", ".xlsx": "Documents", ".ppt": "Documents", ".pptx": "Documents", ".csv": "Documents",
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images", ".bmp": "Images", ".svg": "Images", ".webp": "Images",
    ".mp4": "Video", ".avi": "Video", ".mkv": "Video", ".mov": "Video", ".wmv": "Video", ".flv": "Video",
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".aac": "Audio", ".ogg": "Audio", ".m4a": "Audio",
    ".py": "Code", ".c": "Code", ".cpp": "Code", ".java": "Code", ".kt": "Code", ".dart": "Code", ".js": "Code", ".html": "Code", ".css": "Code", ".json": "Code", ".sh": "Code",
    ".zip": "Archives", ".tar": "Archives", ".gz": "Archives", ".rar": "Archives", ".7z": "Archives"
}

def get_category(ext: str) -> str:
    return EXTENSION_MAP.get(ext.lower(), "Others")