"""Reverse-sync: reconstruct a human-readable file tree from the portal API.

Pulls model files from the portal master via HTTPS and writes them to a local
target directory, maintaining a state file to avoid redundant downloads.

Usage (module form):
    python -m scripts.hydrate_local_tree \\
        --portal-url   http://192.168.2.190:8090 \\
        --target       /mnt/c/Users/ezope/Nextcloud/3d_modelowanie \\
        --token-file   ~/.config/3d-portal/agent.token \\
        --kinds        stl

See --help for full option list.

Exit codes:
    0  — success (possibly with skipped files)
    2  — token file missing or missing credentials
    3  — login 401 (bad credentials)
    4  — portal unreachable
    5  — insufficient disk space on target
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional httpx import — only needed for CLI path.  Tests inject their own
# client, so we don't hard-fail on import if httpx is missing in some env.
# ---------------------------------------------------------------------------
try:
    import httpx as _httpx
except ImportError:  # pragma: no cover
    _httpx = None  # type: ignore[assignment]

_MIN_FREE_BYTES = 1_024 * 1_024 * 1_024  # 1 GiB
_DOWNLOAD_RETRIES = 3
_PAGE_LIMIT = 200


# ---------------------------------------------------------------------------
# Token-file helpers
# ---------------------------------------------------------------------------


def _load_token_file(path: Path) -> dict:
    """Load the agent token JSON file, raising SystemExit on errors."""
    if not path.exists():
        print(f"ERROR: token file not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        print(f"ERROR: cannot parse token file {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    if not data.get("email") or not data.get("password"):
        print(
            "ERROR: token file must have 'email' and 'password' fields.",
            file=sys.stderr,
        )
        sys.exit(2)
    return data


def _save_token_file(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def _token_valid(data: dict) -> bool:
    """Return True if the cached access_token is present and not yet expired."""
    token = data.get("access_token")
    expires_at = data.get("expires_at")
    if not token or not expires_at:
        return False
    try:
        exp = datetime.datetime.fromisoformat(expires_at)
        return exp > datetime.datetime.now(datetime.UTC)
    except (ValueError, TypeError):
        return False


def _do_login(http_client: Any, portal_url: str, email: str, password: str) -> str:
    """POST /api/auth/login, return access_token.  Exits on 401."""
    url = f"{portal_url.rstrip('/')}/api/auth/login"
    try:
        resp = http_client.post(url, json={"email": email, "password": password})
    except Exception as exc:
        print(f"ERROR: portal unreachable ({exc})", file=sys.stderr)
        sys.exit(4)
    if resp.status_code == 401:
        print("ERROR: login 401 — check email and password in token file.", file=sys.stderr)
        sys.exit(3)
    if resp.status_code != 200:
        print(
            f"ERROR: login failed with HTTP {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        sys.exit(4)
    body = resp.json()
    return body["access_token"], body.get("expires_in", 1800)


def ensure_token(http_client: Any, portal_url: str, token_data: dict) -> str:
    """Return a valid bearer token, refreshing if necessary.

    Mutates `token_data` in-place if a new token is obtained.  The caller is
    responsible for writing `token_data` back to disk.
    """
    if _token_valid(token_data):
        return token_data["access_token"]

    access_token, expires_in = _do_login(
        http_client, portal_url, token_data["email"], token_data["password"]
    )
    # Safety margin: treat token as expired 60 s early
    exp = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=expires_in - 60)
    token_data["access_token"] = access_token
    token_data["expires_at"] = exp.isoformat()
    return access_token


# ---------------------------------------------------------------------------
# Category path map builder
# ---------------------------------------------------------------------------


def _build_category_path_map(http_client: Any, headers: dict) -> dict[str, str]:
    """Return {category_uuid: "slug/subslug"} for all categories."""
    resp = http_client.get("/api/categories", headers=headers)
    resp.raise_for_status()
    tree = resp.json()

    path_map: dict[str, str] = {}

    def _walk(nodes: list, prefix: str) -> None:
        for node in nodes:
            slug = node["slug"]
            full = f"{prefix}/{slug}" if prefix else slug
            path_map[node["id"]] = full
            _walk(node.get("children", []), full)

    _walk(tree.get("roots", []), "")
    return path_map


# ---------------------------------------------------------------------------
# SHA256 helpers
# ---------------------------------------------------------------------------


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------


def _download_file(
    http_client: Any,
    headers: dict,
    model_id: str,
    file_id: str,
    dest: Path,
) -> bool:
    """Stream file content to dest.  Returns True on success, False on failure."""
    url = f"/api/models/{model_id}/files/{file_id}/content"
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    for attempt in range(1, _DOWNLOAD_RETRIES + 1):
        try:
            resp = http_client.get(url, headers=headers)
            if resp.status_code != 200:
                print(
                    f"  WARN: GET {url} returned {resp.status_code} (attempt {attempt})",
                    file=sys.stderr,
                )
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(resp.content)
            tmp.rename(dest)
            return True
        except Exception as exc:
            print(f"  WARN: download error {exc} (attempt {attempt})", file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------


def _load_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text())
            if isinstance(data, dict) and data.get("version") == 1:
                return data
        except Exception:
            pass
    return {"version": 1, "paths": {}}


def _save_state(state_path: Path, state: dict, portal_url: str) -> None:
    state["last_run_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    state["portal_url"] = portal_url
    state_path.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Core hydrate logic
# ---------------------------------------------------------------------------


def run_hydrate(
    *,
    http_client: Any,
    portal_url: str = "",
    target: Path,
    kinds: set,
    bearer_token: str = "",
    include_soft_deleted: bool = False,
    prune_deleted: bool = False,
    dry_run: bool = False,
    state_path: Path | None = None,
) -> dict:
    """Run the hydrate.  Returns summary dict.

    Args:
        http_client: Any object with .get/.post(url, **kwargs) methods that
            return a response with .status_code, .json(), .content, .raise_for_status().
            Can be a FastAPI TestClient (for tests) or an httpx.Client (for CLI).
        portal_url: Base URL prefix used for building absolute URLs when the
            client doesn't already have a base URL baked in.  For TestClient,
            pass "" and use relative paths; for httpx.Client with a base_url,
            also pass "".
        target: Local directory to write files into.
        kinds: Set of kind strings (e.g. {"stl", "image"}).
        bearer_token: Bearer token for Authorization header.
        include_soft_deleted: Also sync soft-deleted models.
        prune_deleted: Delete local files not present in master.
        dry_run: If True, make no filesystem changes and don't write state.
        state_path: Path to state JSON file.  Defaults to target/.hydrate-state.json.
    """
    if state_path is None:
        state_path = target / ".hydrate-state.json"

    kinds_set = {str(k) for k in kinds}
    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    # -- 1. Category path map -----------------------------------------------
    category_paths = _build_category_path_map(http_client, headers)

    # -- 2. Load state -------------------------------------------------------
    state = _load_state(state_path)
    paths_state: dict[str, str] = state.setdefault("paths", {})

    # -- 3. Paginate models --------------------------------------------------
    n_models = 0
    m_downloaded = 0
    k_skipped = 0
    p_pruned = 0

    # Track which local relative paths are "owned" by master this run.
    # Used for prune logic.
    master_files: set[str] = set()

    offset = 0
    all_models: list[dict] = []
    while True:
        resp = http_client.get(
            "/api/models",
            headers=headers,
            params={
                "include_deleted": "true" if include_soft_deleted else "false",
                "limit": _PAGE_LIMIT,
                "offset": offset,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        items = body["items"]
        total = body["total"]
        all_models.extend(items)
        offset += len(items)
        if offset >= total or not items:
            break

    n_models = len(all_models)

    for model in all_models:
        model_id = model["id"]
        slug = model["slug"]
        cat_id = model["category_id"]

        cat_path = category_paths.get(cat_id, "uncategorized")

        # Folder name: slug + 8-char short uuid as a stable disambiguator.
        # Prior to E4.4-followup the legacy_id ("001", "002", ...) was preferred
        # when present; the column was dropped 2026-05-11 so all models now
        # use the short-uuid suffix. Existing local trees rendered under the
        # old scheme retain their pre-rename directory names — re-running
        # `hydrate_local_tree.py` against the live API after the schema
        # migration emits the new suffix everywhere; the operator either
        # accepts the layout change OR runs a one-time bulk-rename pass
        # against the pre-migration tree before re-hydrating.
        suffix = model_id.replace("-", "")[:8]
        model_dir_rel = f"{cat_path}/{slug}-{suffix}"
        model_dir = target / model_dir_rel

        # Fetch file list for this model
        files_resp = http_client.get(
            f"/api/models/{model_id}/files",
            headers=headers,
        )
        if files_resp.status_code == 404:
            continue
        files_resp.raise_for_status()
        all_files = files_resp.json()["items"]

        # Filter to requested kinds client-side
        wanted_files = [f for f in all_files if f["kind"] in kinds_set]

        for finfo in wanted_files:
            file_id = finfo["id"]
            original_name = finfo["original_name"]
            master_sha = finfo["sha256"]

            rel_key = f"{model_dir_rel}/{original_name}"
            local_file = target / rel_key
            master_files.add(rel_key)

            # Check state cache
            cached_sha = paths_state.get(rel_key)
            if cached_sha == master_sha:
                k_skipped += 1
                continue

            # Check local disk
            if local_file.exists():
                disk_sha = _sha256_of_file(local_file)
                if disk_sha == master_sha:
                    # In sync, update state cache
                    paths_state[rel_key] = master_sha
                    k_skipped += 1
                    continue

            # Need to download
            if dry_run:
                print(f"  [dry-run] would download: {rel_key}")
                continue

            model_dir.mkdir(parents=True, exist_ok=True)
            ok = _download_file(http_client, headers, model_id, file_id, local_file)
            if ok:
                # Verify sha256
                actual_sha = _sha256_of_file(local_file)
                if actual_sha == master_sha:
                    paths_state[rel_key] = master_sha
                    m_downloaded += 1
                else:
                    print(
                        f"  ERROR: sha256 mismatch after download: {rel_key} "
                        f"(expected {master_sha[:16]}…, got {actual_sha[:16]}…)",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"  ERROR: failed to download after {_DOWNLOAD_RETRIES} attempts: {rel_key}",
                    file=sys.stderr,
                )

    # -- 4. Prune deleted files ----------------------------------------------
    if prune_deleted and not dry_run:
        # Walk state for paths no longer in master
        stale_keys = [k for k in list(paths_state.keys()) if k not in master_files]
        for rel_key in stale_keys:
            local_file = target / rel_key
            if local_file.exists():
                local_file.unlink()
                p_pruned += 1
            del paths_state[rel_key]

    # -- 5. Write state ------------------------------------------------------
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        _save_state(state_path, state, portal_url)

    return {
        "n_models": n_models,
        "m_downloaded": m_downloaded,
        "k_skipped": k_skipped,
        "p_pruned": p_pruned,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Pull model files from the 3D portal API into a local directory tree.",
    )
    p.add_argument(
        "--portal-url", required=True, help="Portal base URL, e.g. http://192.168.2.190:8090"
    )
    p.add_argument("--target", required=True, type=Path, help="Local target directory")
    p.add_argument(
        "--token-file",
        default="~/.config/3d-portal/agent.token",
        type=Path,
        help="Path to agent token JSON file",
    )
    p.add_argument(
        "--kinds",
        default="stl",
        help="Comma-separated list of file kinds (default: stl)",
    )
    p.add_argument(
        "--include-soft-deleted",
        action="store_true",
        help="Also sync soft-deleted models",
    )
    p.add_argument(
        "--prune-deleted",
        action="store_true",
        help="Remove local files not present in master",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    p.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="Path to state file (default: <target>/.hydrate-state.json)",
    )
    args = p.parse_args(argv)

    if _httpx is None:
        print(
            "ERROR: httpx is required for CLI usage. Install it: pip install httpx",
            file=sys.stderr,
        )
        return 1

    target = args.target.expanduser().resolve()
    token_path = args.token_file.expanduser().resolve()
    kinds = {k.strip() for k in args.kinds.split(",") if k.strip()}
    portal_url = args.portal_url.rstrip("/")
    state_path = args.state_file

    # -- Disk space check ---------------------------------------------------
    if target.exists():
        free = shutil.disk_usage(target).free
    else:
        # Check parent
        parent = target.parent
        free = shutil.disk_usage(parent if parent.exists() else Path("/")).free
    if free < _MIN_FREE_BYTES:
        free_gib = free // (1024**3)
        print(
            f"ERROR: insufficient disk space on target ({free_gib} GiB free, need >=1 GiB).",
            file=sys.stderr,
        )
        return 5

    # -- Token --------------------------------------------------------------
    token_data = _load_token_file(token_path)

    # Build a plain httpx.Client (no base_url — we'll use absolute URLs)
    http_client = _httpx.Client(timeout=30)

    try:
        bearer_token = ensure_token(http_client, portal_url, token_data)
        _save_token_file(token_path, token_data)
    except SystemExit:
        http_client.close()
        raise

    # -- Run hydrate --------------------------------------------------------
    try:
        # For CLI we use absolute URLs directly, so portal_url prefix is needed.
        # We monkey-patch the client to prepend portal_url to relative paths.
        summary = run_hydrate(
            http_client=_AbsoluteClient(http_client, portal_url),
            portal_url=portal_url,
            target=target,
            kinds=kinds,
            bearer_token=bearer_token,
            include_soft_deleted=args.include_soft_deleted,
            prune_deleted=args.prune_deleted,
            dry_run=args.dry_run,
            state_path=state_path,
        )
    except Exception as exc:
        print(f"ERROR: hydrate failed: {exc}", file=sys.stderr)
        http_client.close()
        return 4
    finally:
        http_client.close()

    print(
        f"Done. models={summary['n_models']} downloaded={summary['m_downloaded']} "
        f"skipped={summary['k_skipped']} pruned={summary['p_pruned']}"
    )
    return 0


class _AbsoluteClient:
    """Wraps httpx.Client to prepend portal_url to relative paths."""

    def __init__(self, client: Any, base_url: str) -> None:
        self._client = client
        self._base = base_url.rstrip("/")

    def _abs(self, url: str) -> str:
        if url.startswith("/"):
            return self._base + url
        return url

    def get(self, url: str, **kwargs: Any) -> Any:
        return self._client.get(self._abs(url), **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        return self._client.post(self._abs(url), **kwargs)


if __name__ == "__main__":
    sys.exit(main())
