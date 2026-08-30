import os
import tempfile
import time
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

UPLOAD_TEMP_DIR = Path(tempfile.gettempdir()) / "ai-docusearch"
UPLOAD_PREFIX = "ai_docusearch_"


def cleanup_stale_uploads(max_age_seconds: int = 3600) -> None:
    """Remove only expired upload files from the application-owned temp directory."""
    if max_age_seconds < 0 or not UPLOAD_TEMP_DIR.exists():
        return

    cutoff = time.time() - max_age_seconds
    for file_path in UPLOAD_TEMP_DIR.glob(f"{UPLOAD_PREFIX}*"):
        try:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                file_path.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def temporary_upload(filename: str, content: bytes | bytearray | memoryview) -> Iterator[str]:
    """Write upload bytes to a temporary file and always remove it afterward."""
    UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    suffix = os.path.splitext(filename)[1]
    temp_file: BinaryIO = tempfile.NamedTemporaryFile(
        delete=False,
        dir=UPLOAD_TEMP_DIR,
        prefix=UPLOAD_PREFIX,
        suffix=suffix,
    )
    file_path = temp_file.name

    try:
        with temp_file:
            temp_file.write(content)
            temp_file.flush()
        yield file_path
    finally:
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass