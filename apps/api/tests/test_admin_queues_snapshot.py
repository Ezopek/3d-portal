"""Story 34.1 / ADMIN-JOBS-1 — read-only admin ARQ queue console snapshot.

Tests the ``GET /api/admin/queues`` read model (Decisions AO/AP/AQ): a per-pool
queued/running/liveness snapshot plus a "running now" set and a "recent (~last hour)"
list, built ONLY from bounded Redis reads (``zcard`` + bounded ``SCAN``, never ``KEYS``)
and projected through a field allowlist so no pickled ``args``/``kwargs``/``result``
payload can ever leak (NFR22-LEAK-FENCE-1).

All Redis access is faked with ``fakeredis`` seeded with real arq key shapes
(``arq:job:``, ``arq:in-progress:``, ``arq:result:``, ``<queue>:health-check``); the
arq (de)serializers are used to seed so the test exercises the real wire format.
"""

from __future__ import annotations

import inspect
import time
import uuid
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
import pytest_asyncio
from arq.constants import (
    in_progress_key_prefix,
    job_key_prefix,
    result_key_prefix,
)
from arq.jobs import serialize_job, serialize_result
from arq.worker import Worker
from httpx import ASGITransport, AsyncClient

from app.core.auth.jwt import encode_token
from app.main import create_app
from app.modules.queue.admin_router import get_queue_conn

JWT_SECRET = "test-secret-not-real"

# The interval the console MUST surface (Decision AP / AC-7): arq's own
# health_check_interval default, which none of the three pools override. Read it
# from arq here — proving the production value is derived from arq's contract, NOT
# a console-invented literal.
ARQ_DEFAULT_INTERVAL_S = int(inspect.signature(Worker).parameters["health_check_interval"].default)


def _now_ms(offset_s: float = 0.0) -> int:
    return int((time.time() + offset_s) * 1000)


def _token(role: str) -> str:
    return encode_token(subject=str(uuid.uuid4()), role=role, secret=JWT_SECRET, ttl_minutes=30)


async def _seed_queued(fake, queue: str, job_id: str) -> None:
    await fake.zadd(queue, {job_id: float(_now_ms())})


async def _seed_in_progress(
    fake, job_id: str, function: str, *, age_s: float, args=(), kwargs=None
) -> None:
    blob = serialize_job(function, args, kwargs or {}, 1, _now_ms(-age_s))
    await fake.set(job_key_prefix + job_id, blob)
    await fake.set(in_progress_key_prefix + job_id, b"1", px=310_000)


async def _seed_result(
    fake,
    job_id: str,
    function: str,
    queue: str,
    *,
    success: bool,
    result=None,
    started_s_ago: float = 30.0,
    duration_s: float = 5.0,
    args=(),
    kwargs=None,
) -> None:
    start_ms = _now_ms(-started_s_ago)
    finish_ms = _now_ms(-(started_s_ago - duration_s))
    blob = serialize_result(
        function,
        args,
        kwargs or {},
        1,
        start_ms,  # enqueue_time_ms
        success,
        result,
        start_ms,
        finish_ms,
        job_id,  # ref
        queue,
        job_id,
    )
    assert blob is not None
    await fake.set(result_key_prefix + job_id, blob)


async def _seed_health(
    fake,
    queue: str,
    *,
    present: bool = True,
    fresh: bool = True,
    complete: int = 5,
    failed: int = 1,
    retried: int = 0,
    ongoing: int = 1,
    queued: int = 2,
) -> None:
    if not present:
        return
    px = (ARQ_DEFAULT_INTERVAL_S + 1) * 1000 if fresh else 1_000
    info = (
        f"Jun-06 10:00:00 j_complete={complete} j_failed={failed} "
        f"j_retried={retried} j_ongoing={ongoing} queued={queued}"
    )
    await fake.psetex(queue + ":health-check", px, info.encode())


class _NoKeysRedis:
    """Proxy around fakeredis that fails LOUDLY on any unbounded ``KEYS`` call.

    The snapshot path must use ``zcard`` + bounded ``SCAN`` only (AC-8 / NFR22-REDIS-LOAD-1);
    a stray ``KEYS arq:result:*`` (arq's ``all_job_results``) is exactly the broad blocking
    scan the controller forbade. Any ``.keys(...)`` here is a test failure.
    """

    def __init__(self, inner) -> None:
        self._inner = inner

    async def keys(self, *_a, **_k):  # pragma: no cover - must never run
        raise AssertionError("unbounded KEYS is forbidden in the queue snapshot path")

    def __getattr__(self, name):
        return getattr(self._inner, name)


@pytest_asyncio.fixture
async def seam(tmp_path, monkeypatch) -> AsyncIterator[tuple[AsyncClient, object]]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    init_schema(get_engine())

    fake = fakeredis.aioredis.FakeRedis()
    guarded = _NoKeysRedis(fake)
    app.dependency_overrides[get_queue_conn] = lambda: guarded

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        ac.cookies.set("portal_access", _token("admin"))
        yield ac, fake

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _url() -> str:
    return "/api/admin/queues"


# --------------------------------------------------------------------------- AC-1: auth


@pytest.mark.asyncio
async def test_queues_requires_admin_member_is_403(seam) -> None:
    ac, _fake = seam
    ac.cookies.set("portal_access", _token("member"))
    r = await ac.get(_url())
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_queues_requires_admin_agent_is_403(seam) -> None:
    ac, _fake = seam
    ac.cookies.set("portal_access", _token("agent"))
    r = await ac.get(_url())
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_queues_anonymous_is_401(seam) -> None:
    ac, _fake = seam
    ac.cookies.delete("portal_access")
    r = await ac.get(_url())
    assert r.status_code == 401


# --------------------------------------------------------------------- AC-4/AC-5: shape


@pytest.mark.asyncio
async def test_snapshot_three_pools_present_even_when_idle(seam) -> None:
    ac, _fake = seam
    r = await ac.get(_url())
    assert r.status_code == 200
    body = r.json()
    assert {q["name"] for q in body["queues"]} == {"arq:api", "arq:queue", "arq:slicer"}
    assert {q["role"] for q in body["queues"]} == {"api", "render", "slicer"}
    for q in body["queues"]:
        assert q["queued"] == 0
        assert q["running"] == 0
    assert body["running_jobs"] == []
    assert body["recent"] == []
    assert isinstance(body["retention_note"], str) and body["retention_note"]
    assert "generated_at" in body


@pytest.mark.asyncio
async def test_queued_is_exact_via_zcard(seam) -> None:
    ac, fake = seam
    await _seed_queued(fake, "arq:api", "j1")
    await _seed_queued(fake, "arq:api", "j2")
    await _seed_queued(fake, "arq:slicer", "slice:aaaa:bbbb")
    r = await ac.get(_url())
    body = r.json()
    by_name = {q["name"]: q for q in body["queues"]}
    assert by_name["arq:api"]["queued"] == 2
    assert by_name["arq:slicer"]["queued"] == 1
    assert by_name["arq:queue"]["queued"] == 0


# ------------------------------------------------------------- AC-6: running attribution


@pytest.mark.asyncio
async def test_running_jobs_attributed_to_pool_by_function(seam) -> None:
    ac, fake = seam
    await _seed_in_progress(fake, "r1", "render_model", age_s=12)
    await _seed_in_progress(fake, "slice:deadbeef:cafe", "slice_estimate", age_s=3)
    r = await ac.get(_url())
    body = r.json()
    running = {j["job_id"]: j for j in body["running_jobs"]}
    assert running["r1"]["queue"] == "arq:queue"
    assert running["r1"]["function"] == "render_model"
    assert running["r1"]["started_age_s"] >= 0
    assert running["slice:deadbeef:cafe"]["queue"] == "arq:slicer"
    # context.ref is a hash prefix derived from the deterministic slicer job id, never a path
    assert running["slice:deadbeef:cafe"]["context"]["ref"] == "deadbeef"
    by_name = {q["name"]: q for q in body["queues"]}
    assert by_name["arq:queue"]["running"] == 1
    assert by_name["arq:slicer"]["running"] == 1
    assert by_name["arq:api"]["running"] == 0


# ----------------------------------------------------------------- AC-7: liveness tri-state


@pytest.mark.asyncio
async def test_liveness_tristate_alive_idle_unknown(seam) -> None:
    ac, fake = seam
    await _seed_health(fake, "arq:api", present=True, fresh=True)
    await _seed_health(fake, "arq:queue", present=True, fresh=False)
    # arq:slicer left absent
    r = await ac.get(_url())
    body = r.json()
    by_name = {q["name"]: q for q in body["queues"]}
    assert by_name["arq:api"]["worker"]["liveness"] == "alive"
    assert by_name["arq:queue"]["worker"]["liveness"] == "idle"
    assert by_name["arq:slicer"]["worker"]["liveness"] == "unknown"
    # interval is the arq contract default, NOT a console-invented literal
    assert by_name["arq:api"]["worker"]["interval_s"] == ARQ_DEFAULT_INTERVAL_S
    # counters parsed from the health string
    assert by_name["arq:api"]["worker"]["counters"]["complete"] == 5
    assert by_name["arq:api"]["worker"]["counters"]["failed"] == 1
    # unknown pool exposes no counters / heartbeat
    assert by_name["arq:slicer"]["worker"]["counters"] is None
    assert by_name["arq:slicer"]["worker"]["heartbeat_age_s"] is None


# ----------------------------------------------------------------------- AC-8: recent


@pytest.mark.asyncio
async def test_recent_groups_by_queue_and_outcome(seam) -> None:
    ac, fake = seam
    await _seed_result(fake, "ok1", "generate_thumbnail", "arq:api", success=True, duration_s=4)
    await _seed_result(
        fake,
        "bad1",
        "render_model",
        "arq:queue",
        success=False,
        result=ValueError("boom at /etc/secret"),
        duration_s=2,
    )
    r = await ac.get(_url())
    body = r.json()
    recent = {j["job_id"]: j for j in body["recent"]}
    assert recent["ok1"]["queue"] == "arq:api"
    assert recent["ok1"]["outcome"] == "success"
    assert recent["ok1"]["duration_s"] == pytest.approx(4, abs=0.5)
    assert recent["bad1"]["outcome"] == "failed"
    assert recent["bad1"]["error_class"] == "ValueError"


@pytest.mark.asyncio
async def test_recent_respects_hard_cap_and_never_calls_keys(seam) -> None:
    ac, fake = seam
    from app.modules.queue.constants import RECENT_HARD_CAP

    for i in range(RECENT_HARD_CAP + 25):
        await _seed_result(
            fake, f"j{i}", "generate_thumbnail", "arq:api", success=True, duration_s=1
        )
    r = await ac.get(_url())
    body = r.json()
    # The _NoKeysRedis proxy would have raised if an unbounded KEYS ran; reaching here +
    # a capped list proves the bounded-SCAN-with-hard-cap contract.
    assert len(body["recent"]) <= RECENT_HARD_CAP


# --------------------------------------------------------- AC-10/AC-11: leak fence


@pytest.mark.asyncio
async def test_leak_fence_no_payload_fields_in_response(seam) -> None:
    ac, fake = seam
    secret_args = ("/srv/portal/content/models/secret.stl",)
    secret_kwargs = {"token": "super-secret-value", "path": "C:\\Users\\admin\\key.pem"}
    await _seed_in_progress(
        fake, "r1", "render_model", age_s=5, args=secret_args, kwargs=secret_kwargs
    )
    await _seed_result(
        fake,
        "res1",
        "render_model",
        "arq:queue",
        success=True,
        result={"path": "/var/secret/output.png"},
        args=secret_args,
        kwargs=secret_kwargs,
    )
    r = await ac.get(_url())
    raw = r.text
    body = r.json()

    # Allowlist: the serialized DTO carries NO payload keys anywhere.
    assert '"args"' not in raw
    assert '"kwargs"' not in raw
    assert '"result"' not in raw
    assert "super-secret-value" not in raw
    assert "secret.stl" not in raw
    assert "key.pem" not in raw

    allowed_running = {"queue", "function", "job_id", "started_age_s", "context"}
    for j in body["running_jobs"]:
        assert set(j) <= allowed_running
    allowed_recent = {
        "queue",
        "function",
        "outcome",
        "finished_at",
        "duration_s",
        "job_id",
        "context",
        "error_class",
    }
    for j in body["recent"]:
        assert set(j) <= allowed_recent


@pytest.mark.asyncio
async def test_no_path_like_or_secret_substrings_anywhere(seam) -> None:
    ac, fake = seam
    await _seed_in_progress(
        fake,
        "r1",
        "render_model",
        age_s=5,
        args=("/etc/passwd",),
        kwargs={"home": "C:\\secret"},
    )
    await _seed_result(
        fake,
        "res1",
        "render_model",
        "arq:queue",
        success=False,
        result=RuntimeError("failed reading /etc/shadow .. ../escape"),
    )
    r = await ac.get(_url())
    raw = r.text
    # No path separators, drive letters, or parent-dir hops anywhere in the payload.
    assert "/" not in raw
    assert ".." not in raw
    assert "C:\\" not in raw
    assert "passwd" not in raw
    assert "shadow" not in raw
    # error_class is the curated category only
    recent = {j["job_id"]: j for j in r.json()["recent"]}
    assert recent["res1"]["error_class"] == "RuntimeError"


# ------------------------------------------------------------------- AC-12: read-only


def test_queue_module_exposes_only_read_endpoint() -> None:
    from app.modules.queue.admin_router import router

    verbs: set[str] = set()
    paths: set[str] = set()
    for route in router.routes:
        methods = getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        verbs |= methods
        paths.add(getattr(route, "path", ""))
    assert verbs == {"GET"}, f"queue module must be read-only, found verbs={verbs}"
    assert paths == {"/api/admin/queues"}, paths


# ------------------------------------------------------------ AC-2: route-enforcement gate


def test_route_enforcement_gate_passes_without_allowlist_edit() -> None:
    from app.main import _PUBLIC_ROUTES, create_app

    app = create_app()
    assert "/api/admin/queues" not in _PUBLIC_ROUTES
    # find the route and assert it carries an auth Depends (admin gate)
    from fastapi.routing import APIRoute

    target = [r for r in app.routes if isinstance(r, APIRoute) and r.path == "/api/admin/queues"]
    assert target, "queue route not mounted"
    dep_names = {
        getattr(d.call, "__name__", "")
        for d in target[0].dependant.dependencies
        if d.call is not None
    }
    assert "_current_admin_dep" in dep_names
