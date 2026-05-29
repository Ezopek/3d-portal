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
