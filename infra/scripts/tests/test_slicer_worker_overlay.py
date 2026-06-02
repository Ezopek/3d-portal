"""Tests for infra/scripts/slicer-worker-overlay.sh (SW-DEPLOY-1).

Exercises the detection logic and the DRY_RUN shell-command generation
WITHOUT touching Docker or SSH. The `detect` cases build a throwaway temp
git repo (git is available on the dev box; Docker/SSH are not exercised).

Run with the apps/api venv pytest:
    apps/api/.venv/bin/python -m pytest infra/scripts/tests/test_slicer_worker_overlay.py -q
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "slicer-worker-overlay.sh"

# Exit codes the script contracts on.
NEEDED = 0
NOT_NEEDED = 10

# Stable env so command-generation assertions don't depend on the host shell.
BASE_ENV = {
    "PORTAL_VERSION": "0.1.0",
    "PORTAL_HOST": "ezop@192.168.2.190",
    "PORTAL_SSH_PORT": "30022",
    "PORTAL_COMPOSE_DIR": "/mnt/raid/docker-compose/3d-portal",
}


def run(args: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None):
    full_env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    full_env.update(BASE_ENV)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(cwd) if cwd else None,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A temp git repo with one baseline commit; returns the repo dir."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*a: str):
        subprocess.run(
            ["git", "-C", str(repo), *a],
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (repo / "README.md").write_text("base\n")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    return repo


def _commit_file(repo: Path, relpath: str, content: str = "x\n"):
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", f"touch {relpath}"],
        check=True,
        capture_output=True,
    )


# --- detect -----------------------------------------------------------------


def test_detect_needed_on_slicer_module_change(git_repo: Path):
    _commit_file(git_repo, "apps/api/app/modules/slicer/recompute.py")
    res = run(["detect", "HEAD~1..HEAD"], env={"SLICER_REPO_DIR": str(git_repo)})
    assert res.returncode == NEEDED, res.stderr


def test_detect_needed_on_portal_api_base_change(git_repo: Path):
    # Any apps/api change rebuilds portal-api, which the overlay layers FROM.
    _commit_file(git_repo, "apps/api/app/core/config.py")
    res = run(["detect", "HEAD~1..HEAD"], env={"SLICER_REPO_DIR": str(git_repo)})
    assert res.returncode == NEEDED, res.stderr


def test_detect_not_needed_on_docs_only(git_repo: Path):
    _commit_file(git_repo, "docs/operations.md")
    res = run(["detect", "HEAD~1..HEAD"], env={"SLICER_REPO_DIR": str(git_repo)})
    assert res.returncode == NOT_NEEDED, res.stdout + res.stderr


def test_detect_not_needed_on_web_only(git_repo: Path):
    _commit_file(git_repo, "apps/web/src/main.tsx")
    res = run(["detect", "HEAD~1..HEAD"], env={"SLICER_REPO_DIR": str(git_repo)})
    assert res.returncode == NOT_NEEDED, res.stdout + res.stderr


def test_detect_force_overrides_no_change(git_repo: Path):
    _commit_file(git_repo, "docs/operations.md")
    res = run(
        ["detect", "HEAD~1..HEAD"],
        env={"SLICER_REPO_DIR": str(git_repo), "FORCE_SLICER_WORKER_REBUILD": "1"},
    )
    assert res.returncode == NEEDED, res.stderr


def test_detect_empty_range_is_needed(git_repo: Path):
    # No state file + no range arg => cannot scope => safe direction = rebuild.
    res = run(["detect", ""], env={"SLICER_REPO_DIR": str(git_repo)})
    assert res.returncode == NEEDED, res.stderr


# --- DRY_RUN command generation --------------------------------------------


def test_dryrun_rebuild_command():
    res = run(["rebuild"], env={"DRY_RUN": "1"})
    assert res.returncode == 0, res.stderr
    out = res.stdout
    # docker build of the overlay image from the configs-side Dockerfile + context
    assert "docker build" in out
    assert "/mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.Dockerfile" in out
    assert "-t portal-slicer-worker:0.1.0" in out
    # compose bring-up with the overlay file + profile + service
    assert "/mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.yml" in out
    assert "--profile slicer-worker" in out
    assert "up -d slicer-worker" in out
    # over SSH to the target host, never local docker
    assert "ssh" in out and "30022" in out and "ezop@192.168.2.190" in out


def test_dryrun_smoke_command_and_payload():
    res = run(["smoke"], env={"DRY_RUN": "1"})
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert "exec -T slicer-worker python -" in out
    # the four skew classes the smoke must catch
    for mod in (
        "app.modules.slicer.gcode_parse",
        "app.modules.slicer.estimate_store",
        "app.modules.slicer.recompute",
        "app.modules.slicer.overrides",
        "app.modules.slicer.spoolman_invalidation",
    ):
        assert mod in out, f"smoke payload missing module {mod}"
    assert "slicer_estimate_store_dir" in out
    assert "slicer_orca_bin" in out
    assert "parse_gcode_metadata" in out
    assert "map_filament_extra" in out


# --- deploy orchestration (DRY_RUN) ----------------------------------------


def test_deploy_skipped_when_not_needed(git_repo: Path):
    _commit_file(git_repo, "docs/operations.md")
    res = run(
        ["deploy", "HEAD~1..HEAD"],
        env={"SLICER_REPO_DIR": str(git_repo), "DRY_RUN": "1"},
    )
    assert res.returncode == 0, res.stderr
    assert "docker build" not in res.stdout  # no rebuild attempted
    assert "skip" in res.stdout.lower()


def test_deploy_runs_rebuild_and_smoke_when_needed(git_repo: Path):
    _commit_file(git_repo, "apps/api/app/modules/slicer/overrides.py")
    res = run(
        ["deploy", "HEAD~1..HEAD"],
        env={"SLICER_REPO_DIR": str(git_repo), "DRY_RUN": "1"},
    )
    assert res.returncode == 0, res.stderr
    assert "docker build" in res.stdout
    assert "exec -T slicer-worker python -" in res.stdout


def test_deploy_hard_optout(git_repo: Path):
    _commit_file(git_repo, "apps/api/app/modules/slicer/overrides.py")
    res = run(
        ["deploy", "HEAD~1..HEAD"],
        env={
            "SLICER_REPO_DIR": str(git_repo),
            "DRY_RUN": "1",
            "SKIP_SLICER_WORKER": "1",
        },
    )
    assert res.returncode == 0, res.stderr
    assert "docker build" not in res.stdout


def _fake_ssh_dir(tmp_path: Path, *, fail_on: str) -> Path:
    """A throwaway PATH dir holding a fake `ssh` that exits 1 when its remote
    command contains `fail_on` (and 0 otherwise). Lets us prove the rebuild/
    smoke fatality contract with NO real SSH/Docker/network."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    ssh = bindir / "ssh"
    # Does NOT read stdin: the build/compose ssh calls pipe nothing, and the
    # smoke call's ~2KB payload fits the pipe buffer so `printf` completes even
    # if this never drains it. Reading stdin here could block.
    ssh.write_text(
        "#!/usr/bin/env bash\n"
        'for a in "$@"; do\n'
        f'  case "$a" in *"{fail_on}"*) exit 1 ;; esac\n'
        "done\n"
        "exit 0\n"
    )
    ssh.chmod(0o755)
    return bindir


def test_deploy_rebuild_failure_is_fatal(git_repo: Path, tmp_path: Path):
    """Regression for the Gemini Critical: a `docker build` failure MUST abort
    the deploy (non-zero), not be swallowed while `docker compose up` restarts
    the stale image. The fake ssh fails only on the build command, so the smoke
    (which would otherwise return 0) is never reached — the rebuild must gate."""
    _commit_file(git_repo, "apps/api/app/modules/slicer/recompute.py")
    fakebin = _fake_ssh_dir(tmp_path, fail_on="docker build")
    res = run(
        ["deploy", "HEAD~1..HEAD"],
        env={
            "SLICER_REPO_DIR": str(git_repo),
            "PATH": f"{fakebin}:/usr/bin:/bin:/usr/local/bin",
            # DRY_RUN intentionally unset — exercise the real ssh path (faked).
        },
    )
    assert res.returncode != 0, "rebuild failure must abort the deploy (was swallowed?)"
    # the build was attempted but the in-container smoke must NOT have run
    assert "exec -T slicer-worker python -" not in (res.stdout + res.stderr)


def test_deploy_succeeds_when_ssh_ok(git_repo: Path, tmp_path: Path):
    """Counterpart: when the fake ssh succeeds for every remote command, a
    needed deploy runs rebuild + smoke and exits 0 (no real Docker involved)."""
    _commit_file(git_repo, "apps/api/app/modules/slicer/recompute.py")
    fakebin = _fake_ssh_dir(tmp_path, fail_on="\x00never")  # nothing matches
    res = run(
        ["deploy", "HEAD~1..HEAD"],
        env={
            "SLICER_REPO_DIR": str(git_repo),
            "PATH": f"{fakebin}:/usr/bin:/bin:/usr/local/bin",
        },
    )
    assert res.returncode == 0, res.stderr
