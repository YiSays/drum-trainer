import os
from pathlib import Path


def get_storage_dir() -> Path:
    return Path(os.environ.get("STORAGE_DIR", "storage"))
