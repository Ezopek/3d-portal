"""Story 7.4 — config parsing + startup fail-fast tests.

Four named tests T-CONFIG-1..4 — names are binding cross-references for the
dev-story task list (AC-7). Uses per-test monkeypatch + cache-clear pattern
so each test controls ``ENFORCE_2FA_FOR_ROLES`` independently of the
session-scoped fixture in ``conftest.py``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine
from app.main import create_app


def test_default_enforce_2fa_for_roles_is_empty_list(monkeypatch):
    # T-CONFIG-1 — default value with no env override is an empty list.
    monkeypatch.delenv("ENFORCE_2FA_FOR_ROLES", raising=False)
    s = Settings()
    assert s.enforce_2fa_for_roles == []


def test_agent_role_in_enforce_2fa_raises(monkeypatch, tmp_path):
    # T-CONFIG-2 — agent role triggers lifespan-startup fail-fast (Decision F).
    monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", "agent")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    try:
        with (
            pytest.raises(RuntimeError, match="agent role MUST NEVER appear"),
            TestClient(app),
        ):
            pass
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()


def test_csv_parser_parses_member_admin_with_whitespace(monkeypatch):
    # T-CONFIG-3 — CSV string with whitespace + mixed case parses to typed list.
    monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", " member , admin ")
    s = Settings()
    assert s.enforce_2fa_for_roles == [UserRole.member, UserRole.admin]


def test_csv_parser_rejects_unknown_role(monkeypatch):
    # T-CONFIG-4 — unknown role value triggers ValidationError at instantiation.
    monkeypatch.setenv("ENFORCE_2FA_FOR_ROLES", "member,banker")
    with pytest.raises(ValidationError, match="contains unknown role 'banker'"):
        Settings()


def test_spoolman_url_defaults_to_internal_docker_hostname(monkeypatch):
    # Story 31.1 (Decision AE) — P4b primary topology default.
    monkeypatch.delenv("SPOOLMAN_URL", raising=False)
    s = Settings()
    assert s.spoolman_url == "http://spoolman:8000"


def test_spoolman_auth_token_defaults_to_empty_string(monkeypatch):
    # Story 31.1 (Decision AE) — empty default disables ``Authorization``
    # header on the client (MVP-A posture; Phase C trigger sets a real token).
    monkeypatch.delenv("SPOOLMAN_AUTH_TOKEN", raising=False)
    s = Settings()
    assert s.spoolman_auth_token == ""


def test_orca_version_defaults_to_verified_appimage_build(monkeypatch):
    # Story 32.1 (Decision AH/AJ, AC-10) — orca_version is folded into bundle_hash;
    # default pins the verified Linux AppImage build so it is never empty in the
    # hash input. ORCA_VERSION env var overrides it.
    monkeypatch.delenv("ORCA_VERSION", raising=False)
    assert Settings().orca_version == "2.3.2"
    monkeypatch.setenv("ORCA_VERSION", "2.3.3")
    assert Settings().orca_version == "2.3.3"


def test_slicer_artifact_dirs_default_under_portal_content(monkeypatch):
    # Story 32.1 (AC-2/AC-6/AC-12) — vendored-artifact + bundle-store roots default
    # to container-internal paths on the portal-content volume, never a bench path.
    # The bundle-store default is the store ROOT; BundleStore adds the internal
    # ``bundles/`` + ``snapshots/`` children (review fix #5 — no double-nesting).
    monkeypatch.delenv("SLICER_VENDORED_PROFILES_DIR", raising=False)
    monkeypatch.delenv("SLICER_BUNDLE_STORE_DIR", raising=False)
    s = Settings()
    assert str(s.slicer_vendored_profiles_dir) == "/data/content/slicer/vendored"
    assert str(s.slicer_bundle_store_dir) == "/data/content/slicer"


# --- Story 32.2 (AC-9/AC-10) — slicer-worker settings slots --------------------


def test_slicer_orca_bin_defaults_to_container_internal_entrypoint(monkeypatch):
    # Story 32.2 (AC-9/AC-10) — the Orca entrypoint is read from a settings slot,
    # NEVER a hard-coded literal. Default is a container-internal path (the
    # --appimage-extract entrypoint inside the configs-side slicer-worker
    # container); the live value is set by the configs recipe (AC-12).
    monkeypatch.delenv("ORCA_BIN", raising=False)
    monkeypatch.delenv("SLICER_ORCA_BIN", raising=False)
    assert Settings().slicer_orca_bin == "/opt/orca/orca"


def test_slicer_orca_bin_reads_orca_bin_env(monkeypatch):
    # AC-12 contract: the configs-side slicer-worker container sets ORCA_BIN; the
    # portal Settings field MUST read it (the name-aligned SLICER_ORCA_BIN var that
    # the settings-env-compose drift gate expects is accepted too — AliasChoices).
    monkeypatch.delenv("SLICER_ORCA_BIN", raising=False)
    monkeypatch.setenv("ORCA_BIN", "/opt/orca/squashfs-root/AppRun")
    assert Settings().slicer_orca_bin == "/opt/orca/squashfs-root/AppRun"


def test_slicer_stl_cache_dir_defaults_under_portal_content(monkeypatch):
    # AC-4/AC-9 — content-hash STL cache root defaults under the portal-content
    # volume (mirrored catalog copy lands here at enqueue); never an external path.
    monkeypatch.delenv("SLICER_STL_CACHE_DIR", raising=False)
    assert str(Settings().slicer_stl_cache_dir) == "/data/content/slicer/stl-cache"


def test_slicer_max_concurrency_defaults_to_bounded_one(monkeypatch):
    # AC-7/AC-10 (NFR20-RESOURCE-1) — small bounded cap so a minutes-long slice
    # cannot starve API/render workers on .190. Default 1; configurable up if
    # headroom allows, but the default must stay small.
    monkeypatch.delenv("SLICER_MAX_CONCURRENCY", raising=False)
    s = Settings()
    assert s.slicer_max_concurrency == 1
    assert s.slicer_max_concurrency <= 2


def test_slicer_timeouts_default_to_conservative_pending_benchmark(monkeypatch):
    # AC-7/AC-10 — ARBITRARY conservative defaults pending the configs-side R3
    # slice-wall-time benchmark (TB-016 lesson: not a contractual constant). The
    # --info pre-check carries its own short ceiling (sub-slice fast by design).
    monkeypatch.delenv("SLICER_SLICE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("SLICER_INFO_TIMEOUT_SECONDS", raising=False)
    s = Settings()
    assert s.slicer_slice_timeout_seconds == 900
    assert s.slicer_info_timeout_seconds == 60
