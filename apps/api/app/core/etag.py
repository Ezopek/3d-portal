import hashlib
from pathlib import Path


def file_etag(path: Path) -> str:
    st = path.stat()
    raw = f"{st.st_size}-{int(st.st_mtime_ns)}".encode()
    # SHA-1 is used here as a non-cryptographic hash for HTTP ETag generation
    # (cache-key only; no integrity/authentication semantics). `usedforsecurity=False`
    # silences bandit B324 and signals the same intent to OpenSSL FIPS mode.
    return f'W/"{hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:16]}"'
