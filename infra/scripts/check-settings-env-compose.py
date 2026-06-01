#!/usr/bin/env python3
"""Story 8.1 (Epic 7 retro §1) — Settings ↔ env.example ↔ docker-compose.yml diff.

Catches the Story 6.4 / 6.6 / 6.7 / 7.1 recurring regression class: a new
Settings field shipped, env.example updated, but the docker-compose env
block missed the wiring (or vice versa). The stage runs in check-all.sh
as ``settings-env-compose-diff`` and fails with a structured error when
the three surfaces drift.

Invocation: ``apps/api/.venv/bin/python infra/scripts/check-settings-env-compose.py``
Exit codes: 0 on green, 1 on drift detected. Output is human-readable
diagnostics on stderr/stdout suitable for the check-all.sh stage banner.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# KNOWN_INFRA_ONLY — env.example vars that are deliberately NOT in the
# Pydantic Settings class. Either host-side paths consumed by docker-compose
# volume mounts (CATALOG_HOST_DIR, etc.), build-time-only vars baked into
# images (VITE_*, GLITCHTIP_*), or operator-facing display vars (PORTAL_VERSION
# is in Settings as portal_version but listed here as a documented exception
# per story §AC-6 step 1).
KNOWN_INFRA_ONLY: frozenset[str] = frozenset(
    {
        "CATALOG_HOST_DIR",
        "RENDERS_HOST_DIR",
        "STATE_HOST_DIR",
        "CACHE_HOST_DIR",
        "CONTENT_HOST_DIR",
        # Frontend / build-time / GlitchTip — never read by the Pydantic Settings.
        "VITE_SENTRY_DSN",
        "VITE_GIT_COMMIT",
        "VITE_BUILD_TIME",
        "VITE_BUILD_HOST",
        "GLITCHTIP_AUTH_TOKEN",
        "GLITCHTIP_ORG_SLUG",
        "GLITCHTIP_PROJECT_SLUG",
        # Bench-only one-time export path (Story 32.1) — snapshots the Orca
        # system+user profile tree into the vendored artifact set. NEVER read by
        # production runtime (NFR20-CONTAINER-1); not a Pydantic Settings field.
        "FENRIR_EXPORT_PATH",
    }
)

# Settings fields that are intentionally NOT exposed via env.example —
# either internal defaults (app_name, jwt_algorithm, etc.), container-side
# paths hardcoded in docker-compose env block (catalog_data_dir, etc.),
# or per-test/dev overrides that don't ship as documented operator knobs.
SETTINGS_NO_ENV_OVERRIDE: frozenset[str] = frozenset(
    {
        # Internal defaults — never expect operator override
        "app_name",
        "app_version",
        "jwt_algorithm",
        "jwt_ttl_minutes",
        "download_extensions",
        # Container-side paths — hardcoded in compose env, not in env.example
        "catalog_data_dir",
        "renders_dir",
        "state_dir",
        "catalog_cache_dir",
        "portal_content_dir",
        # URLs hardcoded in compose env to the in-network service name
        "database_url",
        "redis_url",
        # Settings shape that has no env binding (computed property, etc.)
        # — currently none, but the slot is reserved for future expansion.
    }
)


def _settings_fields() -> set[str]:
    """Read the Settings class field names without importing the app.

    Avoids pulling in app.core.config (and its transitive imports of
    SQLModel / Pydantic / FastAPI) so the script stays cheap to run.
    """
    cfg = Path(__file__).resolve().parents[2] / "apps/api/app/core/config.py"
    text = cfg.read_text()
    # Match ``    field_name: Type = ...`` at class-body indent. Excludes
    # ``model_config`` (assigned, not annotated) and method definitions.
    fields = set()
    pattern = re.compile(r"^    ([a-z_][a-z_0-9]*)\s*:\s*[A-Za-z]", re.MULTILINE)
    for match in pattern.finditer(text):
        name = match.group(1)
        # Filter false positives — only annotated class-body fields.
        if name.startswith("_") or name == "model_config":
            continue
        fields.add(name)
    return fields


def _env_example_vars() -> set[str]:
    """Top-level uppercase-snake var names declared in infra/env.example.

    Picks up BOTH uncommented declarations (``VAR=value``) AND commented
    optional-override declarations (``# VAR=value``). Commented-out vars
    are still "documented" — operators discover them by reading the file.
    The spec's "ignore comments" wording is interpreted at the line level
    (skip pure prose comments), not at the declaration level (a commented
    var is still a declaration). See story §AC-6 step 1 implementer's
    call clause.
    """
    path = Path(__file__).resolve().parents[1] / "env.example"
    vars_ = set()
    # Match optional "# " prefix followed by VAR= form.
    pattern = re.compile(r"^#?\s*([A-Z][A-Z_0-9]*)=")
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = pattern.match(stripped)
        if match:
            vars_.add(match.group(1))
    return vars_


def _compose_env_vars() -> set[str]:
    """All ``${VAR...}`` references inside the api + arq-worker environment blocks.

    Scope: ONLY the api + arq-worker service ``environment:`` blocks per
    story §AC-6 step 1. The web service's environment / build args are
    handled by the VITE_* allow-list in KNOWN_INFRA_ONLY. Volume mounts
    (CATALOG_HOST_DIR etc.) live in services.api.volumes — they're scanned
    separately because the diff rule for them is "must appear in env.example
    AND in KNOWN_INFRA_ONLY".
    """
    path = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    text = path.read_text()

    # Carve out the api + arq-worker environment blocks. Both follow the
    # shape "  serv:\n    ...\n    environment:\n      KEY: ${VAR}\n ..."
    # until the next 4-space-indented key or a less-indented line.
    env_var_pattern = re.compile(r"\$\{([A-Z][A-Z_0-9]*)")
    vars_ = set()

    for service_name in ("api", "arq-worker"):
        # Find the service block start.
        marker = f"\n  {service_name}:\n"
        start = text.find(marker)
        if start < 0:
            continue
        # Find the environment: subsection within the service block.
        env_idx = text.find("    environment:", start)
        if env_idx < 0:
            continue
        # Find the next 4-space-indented YAML key (end of environment block).
        rest = text[env_idx + len("    environment:") :]
        # Match the indented (6+ space) lines that belong to environment.
        block_lines: list[str] = []
        for ln in rest.splitlines():
            if not ln:
                continue
            if ln.startswith("      "):
                block_lines.append(ln)
            elif ln.startswith("    ") and ln.lstrip().endswith(":"):
                # Next 4-space-indented key — end of environment block.
                break
            elif ln.startswith("  ") and not ln.startswith("    "):
                # Next service definition — end.
                break
        for ln in block_lines:
            for match in env_var_pattern.finditer(ln):
                vars_.add(match.group(1))

    return vars_


def main() -> int:
    settings = _settings_fields()
    env_example = _env_example_vars()
    compose_env = _compose_env_vars()

    expected_in_env = {f.upper() for f in settings if f not in SETTINGS_NO_ENV_OVERRIDE}
    errors: list[str] = []

    missing_in_env_example = expected_in_env - env_example
    if missing_in_env_example:
        errors.append(
            "Settings fields NOT documented in infra/env.example:\n  - "
            + "\n  - ".join(sorted(missing_in_env_example))
        )

    missing_in_compose = expected_in_env - compose_env
    if missing_in_compose:
        errors.append(
            "Settings fields NOT wired in infra/docker-compose.yml (api or "
            "arq-worker environment block):\n  - "
            + "\n  - ".join(sorted(missing_in_compose))
        )

    settings_upper = {f.upper() for f in settings}
    orphan_env_vars = env_example - settings_upper - KNOWN_INFRA_ONLY
    if orphan_env_vars:
        errors.append(
            "env.example vars with NO matching Settings field "
            "(add to SETTINGS_NO_ENV_OVERRIDE or KNOWN_INFRA_ONLY allowlist):\n  - "
            + "\n  - ".join(sorted(orphan_env_vars))
        )

    if errors:
        sys.stderr.write("[settings-env-compose-diff] FAIL\n\n")
        sys.stderr.write("\n\n".join(errors))
        sys.stderr.write("\n")
        return 1

    print(
        f"[settings-env-compose-diff] OK — "
        f"{len(settings)} Settings fields / "
        f"{len(env_example)} env.example vars / "
        f"{len(compose_env)} compose env refs aligned"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
