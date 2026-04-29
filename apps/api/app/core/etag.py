import hashlib
from pathlib import Path


def file_etag(path: Path) -> str:
    st = path.stat()
    raw = f"{st.st_size}-{int(st.st_mtime_ns)}".encode()
    return f'W/"{hashlib.sha1(raw).hexdigest()[:16]}"'
