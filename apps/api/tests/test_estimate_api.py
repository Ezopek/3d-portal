"""Story 32.6 — narrow estimate read/resolve API seam tests (AC-1, AC-5, AC-8).

The seam under test:
  - ``app.modules.slicer.schemas`` — the UI-safe ``extra="forbid"`` DTOs (no
    ``settings_ids`` / ``bundle_hash`` / Orca-key / g-code field exists on them).
  - ``app.modules.slicer.router`` — the authenticated ``GET /api/estimates`` read
    endpoint: ``validate_content_hash`` the caller ``stl_hash``, resolve the preset
    to a ``bundle_hash`` (injected resolver), ``EstimateStore.read`` the record, and
    project it onto the DTO. A miss ⇒ ``status="absent"`` (a 200, not a 404).
  - ``app.modules.slicer.estimate_read`` — the pure projection + override-context
    builders.

No real Orca / worker / Redis / vendored profiles: the resolver is injected via
``app.dependency_overrides`` (a fake returning a fixed ``bundle_hash`` + optional
pinned filament), and the ``EstimateStore`` is a real store rooted at ``tmp_path``
seeded with ``EstimateRecord``s built in-process. ``computed_at`` is a fixed string
so the assertions stay clock-free (AC-12).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import quote

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.auth.jwt import encode_token
from app.main import create_app
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.enqueue import slice_job_id
from app.modules.slicer.estimate_read import (
    PresetResolveError,
    ResolvedPreset,
    SettingsEstimateResolver,
)
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import (
    EstimateFailureReason,
    EstimateRecord,
    EstimateStatus,
    PrintIntentPreset,
    ResolveSuccess,
    SliceWarning,
)
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.router import (
    get_arq_pool,
    get_estimate_resolver,
    get_estimate_store,
    get_recompute_resolver,
)
from app.modules.slicer.schemas import EstimateView, OverrideContextView, WarningView
from app.modules.slicer.validation import NullCliValidator
from app.modules.slicer.worker import SLICER_QUEUE_NAME
from app.modules.slicer.worker_job import SLICE_JOB_NAME
from app.modules.spools.models import SpoolmanFilament

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

STL_HASH = "a" * 64
BUNDLE_HASH = "b" * 64
COMPUTED_AT = "2026-06-02T10:00:00+00:00"


# === record builders =========================================================


def _fresh(**kw) -> EstimateRecord:
    base = dict(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        time_seconds=12947,
        filament_g=76.76,
        filament_mm=25735.79,
        filament_cm3=61.90,
        filament_cost=4.60,
        settings_ids={"filament_settings_id": "AI Rosa3D PLA Starter"},
        warnings=[SliceWarning(message="floating cantilever")],
        status=EstimateStatus.fresh,
        computed_at=COMPUTED_AT,
    )
    base.update(kw)
    return EstimateRecord(**base)


def _failed() -> EstimateRecord:
    return EstimateRecord(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        status=EstimateStatus.failed,
        reason=EstimateFailureReason.unparseable_time,
        computed_at=COMPUTED_AT,
    )


def _stale() -> EstimateRecord:
    return _fresh(status=EstimateStatus.stale)


def _queued() -> EstimateRecord:
    return _fresh(status=EstimateStatus.queued)


# === fake resolver ===========================================================


class _FakeResolver:
    """Injected resolver: returns a fixed ``bundle_hash`` (+ optional pinned filament).

    Records whether ``resolve_preset`` was called so the malformed-hash test can
    assert the resolve was short-circuited BEFORE any resolve attempt.
    """

    def __init__(self, *, pinned: SpoolmanFilament | None = None) -> None:
        self.called = False
        self.pinned = pinned
        # When set, ``resolve_preset`` raises ``PresetResolveError`` (the 422 path) — lets a
        # recompute test exercise the unresolvable-preset branch without a second resolver type.
        self.fail_reason: str | None = None

    async def resolve_preset(self, intent: PrintIntentPreset) -> ResolvedPreset:
        self.called = True
        if self.fail_reason is not None:
            raise PresetResolveError(self.fail_reason)
        return ResolvedPreset(bundle_hash=BUNDLE_HASH, pinned_filament=self.pinned)


# === fixture =================================================================


@pytest_asyncio.fixture
async def seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, EstimateStore, _FakeResolver]]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    init_schema(get_engine())

    fake_redis = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake_redis)

    async def _aclose() -> None:
        return None

    factory.aclose = _aclose
    app.state.redis = factory

    store = EstimateStore(tmp_path / "estimates-root")
    resolver = _FakeResolver()
    app.dependency_overrides[get_estimate_store] = lambda: store
    app.dependency_overrides[get_estimate_resolver] = lambda: resolver

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, store, resolver

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _member_cookie() -> str:
    return encode_token(subject=str(uuid.uuid4()), role="member", secret="test", ttl_minutes=30)


def _read_url(
    *,
    stl_hash: str = STL_HASH,
    material_class: str = "PLA",
    quality_tier: str = "standard",
    printer_ref: str = "p1s",
    spoolman_filament_ref: str | None = None,
) -> str:
    url = (
        f"/api/estimates?stl_hash={stl_hash}&material_class={material_class}"
        f"&quality_tier={quality_tier}&printer_ref={printer_ref}"
    )
    if spoolman_filament_ref is not None:
        url += f"&spoolman_filament_ref={quote(spoolman_filament_ref, safe='')}"
    return url


# === AC-1 — DTO no-leak =======================================================


def test_estimate_dto_excludes_settings_ids_and_internals():
    """The UI-safe DTOs are ``extra="forbid"`` and carry NO internal field.

    A ``settings_ids`` / ``bundle_hash`` / ``stl_hash`` / Orca-key / g-code field
    must not exist on ``EstimateView`` or ``OverrideContextView`` — the FR20-PRESET-1
    no-internal-leak contract enforced at the schema edge.
    """
    leak_fields = {
        "settings_ids",
        "bundle_hash",
        "stl_hash",
        "machine",
        "process",
        "filament",
        "filament_max_volumetric_speed",
        "nozzle_temperature",
        "filament_density",
        "gcode",
        "source_snapshot_ref",
        "spoolman_overrides_ref",
    }
    assert leak_fields.isdisjoint(EstimateView.model_fields)
    assert leak_fields.isdisjoint(OverrideContextView.model_fields)

    ctx = OverrideContextView(material_class="PLA", quality_tier="standard")
    with pytest.raises(ValidationError):
        EstimateView(status="absent", override_context=ctx, settings_ids={"x": "y"})
    with pytest.raises(ValidationError):
        EstimateView(status="absent", override_context=ctx, bundle_hash=BUNDLE_HASH)


@pytest.mark.asyncio
async def test_read_endpoint_resolves_preset_to_bundle_and_reads_record(seam):
    ac, store, resolver = seam
    store.write(_fresh())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url())
    assert r.status_code == 200
    body = r.json()
    assert resolver.called is True
    assert body["status"] == "fresh"
    assert body["time_seconds"] == 12947
    assert body["filament_g"] == 76.76
    assert body["filament_mm"] == 25735.79
    assert body["filament_cm3"] == 61.90
    assert body["filament_cost"] == 4.60
    assert body["computed_at"] == COMPUTED_AT
    assert body["failure_reason"] is None
    assert body["warnings"] == [{"code": "slice_warning", "message": "floating cantilever"}]
    assert body["override_context"]["material_class"] == "PLA"
    assert body["override_context"]["quality_tier"] == "standard"


@pytest.mark.asyncio
async def test_read_endpoint_absent_record_returns_status_absent_not_404(seam):
    ac, _store, _resolver = seam
    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url())
    assert r.status_code == 200  # NOT 404 — absent is a first-class UI state
    body = r.json()
    assert body["status"] == "absent"
    assert body["time_seconds"] is None
    assert body["filament_g"] is None
    assert body["filament_cost"] is None
    assert body["computed_at"] is None
    assert body["failure_reason"] is None
    # override_context still present (material/tier are known from the preset).
    assert body["override_context"]["material_class"] == "PLA"


@pytest.mark.asyncio
async def test_read_endpoint_requires_auth(seam):
    ac, _store, _resolver = seam
    r = await ac.get(_read_url())  # no cookie
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_read_endpoint_rejects_malformed_stl_hash(seam):
    ac, _store, resolver = seam
    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url(stl_hash="not-a-valid-hash"))
    assert r.status_code == 422
    # The resolve MUST NOT be attempted on a malformed hash (path-safety + no work on garbage).
    assert resolver.called is False


@pytest.mark.asyncio
async def test_read_endpoint_projects_failed_record_with_reason(seam):
    ac, store, _resolver = seam
    store.write(_failed())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert body["failure_reason"] == "unparseable_time"
    # numerics are em-dash-on-the-FE None here, NEVER 0 (the no-silent-zero contract).
    assert body["time_seconds"] is None
    assert body["filament_g"] is None
    assert body["filament_cost"] is None


@pytest.mark.asyncio
async def test_read_endpoint_rejects_unsupported_material_class(seam):
    ac, _store, resolver = seam
    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url(material_class="ABS"))  # outside the FR20 set
    assert r.status_code == 422
    assert resolver.called is False


# === AC-8 — no-raw-internals on the response body =============================


@pytest.mark.asyncio
async def test_read_response_body_carries_no_internal_field_names(seam):
    ac, store, _resolver = seam
    store.write(_fresh())
    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url())
    assert r.status_code == 200
    raw = r.text
    for internal in (
        "settings_ids",
        "bundle_hash",
        "stl_hash",
        "source_snapshot_ref",
        "spoolman_overrides_ref",
        "filament_max_volumetric_speed",
        "nozzle_temperature",
        "filament_density",
        "gcode",
    ):
        assert internal not in raw, f"internal field {internal!r} leaked into the response body"


# === AC-5 — override-context (pinned Spoolman filament), no value leak =========


@pytest.mark.asyncio
async def test_read_endpoint_pinned_filament_override_context_no_value_leak(seam):
    ac, store, resolver = seam
    store.write(_fresh())

    # The injected resolver returns this pinned filament for the override-context build.
    resolver.pinned = SpoolmanFilament(
        id=10,
        name="PLA Speed Matt White",
        vendor_name="Bambu Lab",
        material="PLA",
        extra={
            # mapped override VALUES that must NEVER reach the DTO/body:
            "filament_max_volumetric_speed": "8.0",
            "nozzle_temperature": "215",
            "filament_density": "1.24",
            # the carried purchase link Story 32.6 surfaces (JSON-encoded string):
            "url": '"https://shop.example.com/pla-white"',
        },
    )

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.get(_read_url(spoolman_filament_ref="Bambu Lab\x1fPLA\x1fPLA Speed Matt White"))
    assert r.status_code == 200
    body = r.json()
    ctx = body["override_context"]
    assert ctx["pinned_filament_name"] == "PLA Speed Matt White"
    assert ctx["custom_overrides_applied"] is True
    assert ctx["purchase_url"] == "https://shop.example.com/pla-white"
    # The override VALUES must not appear anywhere in the body (only the FACT + safe metadata).
    raw = r.text
    assert "8.0" not in raw
    assert "215" not in raw
    assert "1.24" not in raw


def test_warning_view_is_extra_forbid():
    with pytest.raises(ValidationError):
        WarningView(code="x", message="y", extra_field="leak")


# === review blocker #1 — the PRODUCTION resolver read path is NON-MUTATING ======

_RESOLVABLE_INTENT = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)


@pytest.mark.asyncio
async def test_production_resolver_read_path_does_not_mutate_bundle_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An absent-estimate read via the PRODUCTION resolver writes NO bundle-store file.

    ``GET /api/estimates`` is documented + intended read-only, but Story 32.1 ``resolve``
    persists a fresh bundle + provenance snapshot on a content MISS. The read path wraps
    the store in a ``_ReadOnlyBundleStore`` (review blocker #1), so a resolve over a cold
    store leaves the on-disk bundle/snapshot artifacts untouched. This exercises the REAL
    ``SettingsEstimateResolver`` against the checked-in vendored fixtures (NOT the injected
    fake resolver), so the no-write guarantee is proven on the production code path — the
    exact mutation the reviewer flagged.
    """
    from app.core.config import get_settings

    bundle_root = tmp_path / "bundle-store"
    control_root = tmp_path / "control-store"
    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(FIXTURES))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(bundle_root))
    monkeypatch.setenv("ORCA_VERSION", "2.3.2")
    get_settings.cache_clear()
    try:
        # Guard: the SAME resolve against a WRITING store DOES persist — proving the cold
        # store actually reaches the write step, so the no-write assertion below is not
        # vacuously green (e.g. via an early resolve failure or a cache hit before any
        # write). The control store lives OUTSIDE the configured bundle-store root.
        writing = BundleStore(control_root)
        control = resolve(
            _RESOLVABLE_INTENT,
            source=VendoredProfileSource(FIXTURES),
            store=writing,
            override_provider=NoopOverrideProvider(),
            validator=NullCliValidator(),
            orca_version="2.3.2",
        )
        assert isinstance(control, ResolveSuccess)
        assert list(control_root.rglob("*.json")), (
            "control resolve must write — otherwise the no-write test is vacuous"
        )

        # The production read-path resolver against the REAL (settings-wired) store root.
        resolver = SettingsEstimateResolver(redis_factory=None)
        resolved = await resolver.resolve_preset(_RESOLVABLE_INTENT)
        # Same computed bundle_hash — the read path resolves identically, it just does not persist.
        assert resolved.bundle_hash == control.bundle.bundle_hash

        # … and it persisted NOTHING under the production bundle-store root.
        written = list(bundle_root.rglob("*.json")) if bundle_root.exists() else []
        assert written == [], f"read path mutated the bundle store: {written}"
    finally:
        get_settings.cache_clear()


# === EST-RECOMPUTE-1 — guarded POST /api/estimates/recompute ===================
#
# The enqueue seam under test: the authenticated POST validates the stl_hash, resolves the
# preset to a bundle_hash via the SAME resolver seam (here a fake), and enqueues an idempotent
# by-hash re-slice through the Story 32.4 `enqueue_recompute` helper — guarded so an already
# `queued` record does NOT re-enqueue, and never fabricating numbers for an absent/failed key.
# A fake arq pool records the enqueue so the deterministic Story 32.4 job-id / queue kwargs are
# assertable without a live Redis; no real Orca / worker runs.


class _FakeArqPool:
    """Records ``enqueue_job`` calls so a test can assert the Story 32.4 enqueue kwargs."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


@pytest_asyncio.fixture
async def recompute_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, EstimateStore, _FakeResolver, _FakeArqPool]]:
    """Mirror of ``seam`` for the POST recompute endpoint: also overrides the recompute
    resolver seam and installs a fake arq pool via the ``get_arq_pool`` dependency seam.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine, init_schema

    get_settings.cache_clear()
    get_engine.cache_clear()

    app = create_app()
    init_schema(get_engine())

    store = EstimateStore(tmp_path / "estimates-root")
    resolver = _FakeResolver()
    arq_pool = _FakeArqPool()
    app.dependency_overrides[get_estimate_store] = lambda: store
    app.dependency_overrides[get_recompute_resolver] = lambda: resolver
    app.dependency_overrides[get_arq_pool] = lambda: arq_pool

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Portal-Client": "web"},
    ) as ac:
        yield ac, store, resolver, arq_pool

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    get_engine.cache_clear()


def _recompute_body(
    *,
    stl_hash: str = STL_HASH,
    material_class: str = "PLA",
    quality_tier: str = "standard",
    printer_ref: str = "p1s",
    spoolman_filament_ref: str | None = None,
) -> dict:
    body = {
        "stl_hash": stl_hash,
        "material_class": material_class,
        "quality_tier": quality_tier,
        "printer_ref": printer_ref,
    }
    if spoolman_filament_ref is not None:
        body["spoolman_filament_ref"] = spoolman_filament_ref
    return body


@pytest.mark.asyncio
async def test_recompute_requires_auth(recompute_seam):
    ac, _store, resolver, arq_pool = recompute_seam
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())  # no cookie
    assert r.status_code == 401
    # No work on an unauthenticated request — neither resolve nor enqueue.
    assert resolver.called is False
    assert arq_pool.calls == []


@pytest.mark.asyncio
async def test_recompute_rejects_malformed_stl_hash_before_resolve_or_enqueue(recompute_seam):
    ac, _store, resolver, arq_pool = recompute_seam
    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body(stl_hash="not-a-hash"))
    assert r.status_code == 422
    # Path-safety gate fires BEFORE any resolve/store/queue work (no garbage hash in a _job_id).
    assert resolver.called is False
    assert arq_pool.calls == []


@pytest.mark.asyncio
async def test_recompute_unresolvable_preset_returns_422_without_enqueue(recompute_seam):
    ac, _store, resolver, arq_pool = recompute_seam
    resolver.fail_reason = "unsupported_printer"  # the preset classifies as unresolvable

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 422
    assert resolver.called is True
    # A preset with no bundle never enqueues a job.
    assert arq_pool.calls == []


@pytest.mark.asyncio
async def test_recompute_already_queued_is_idempotent_no_enqueue(recompute_seam):
    ac, store, _resolver, arq_pool = recompute_seam
    store.write(_queued())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    body = r.json()
    # The R1 self-DoS guard: a recompute already in flight does NOT re-enqueue.
    assert body["enqueued"] is False
    assert arq_pool.calls == []
    # The still-servable queued estimate is returned, projected honestly.
    assert body["estimate"]["status"] == "queued"
    assert body["estimate"]["filament_g"] == 76.76


@pytest.mark.asyncio
async def test_recompute_fresh_enqueues_once_and_marks_queued(recompute_seam):
    ac, store, _resolver, arq_pool = recompute_seam
    store.write(_fresh())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    body = r.json()
    assert body["enqueued"] is True
    # Enqueued exactly once.
    assert len(arq_pool.calls) == 1
    # The persisted record transitioned fresh → queued (still carrying its numbers).
    persisted = store.read(STL_HASH, BUNDLE_HASH)
    assert persisted is not None and persisted.status == EstimateStatus.queued
    assert persisted.filament_g == 76.76
    # The response reflects the queued transition, still servable.
    assert body["estimate"]["status"] == "queued"
    assert body["estimate"]["filament_g"] == 76.76


@pytest.mark.asyncio
async def test_recompute_stale_enqueues_once_and_marks_queued(recompute_seam):
    ac, store, _resolver, arq_pool = recompute_seam
    store.write(_stale())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    body = r.json()
    assert body["enqueued"] is True
    assert len(arq_pool.calls) == 1
    persisted = store.read(STL_HASH, BUNDLE_HASH)
    assert persisted is not None and persisted.status == EstimateStatus.queued
    assert body["estimate"]["status"] == "queued"


@pytest.mark.asyncio
async def test_recompute_absent_enqueues_without_fabricated_numbers(recompute_seam):
    ac, store, _resolver, arq_pool = recompute_seam  # no record seeded ⇒ a miss

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    body = r.json()
    # Enqueued so the worker can fill the absent key, but NO record is fabricated.
    assert body["enqueued"] is True
    assert len(arq_pool.calls) == 1
    assert store.read(STL_HASH, BUNDLE_HASH) is None  # still a genuine miss
    est = body["estimate"]
    assert est["status"] == "absent"
    assert est["time_seconds"] is None
    assert est["filament_g"] is None
    assert est["filament_cost"] is None


@pytest.mark.asyncio
async def test_recompute_failed_enqueues_without_fabricated_numbers(recompute_seam):
    ac, store, _resolver, arq_pool = recompute_seam
    store.write(_failed())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    body = r.json()
    # A failed key re-queues (worker retry) but is NOT "queued over" a good number — it stays
    # failed in the store (mark_queued no-ops on failed) and projects honestly.
    assert body["enqueued"] is True
    assert len(arq_pool.calls) == 1
    persisted = store.read(STL_HASH, BUNDLE_HASH)
    assert persisted is not None and persisted.status == EstimateStatus.failed
    est = body["estimate"]
    assert est["status"] == "failed"
    assert est["failure_reason"] == "unparseable_time"
    assert est["time_seconds"] is None
    assert est["filament_g"] is None


@pytest.mark.asyncio
async def test_recompute_uses_deterministic_story_324_enqueue_kwargs(recompute_seam):
    ac, store, _resolver, arq_pool = recompute_seam
    store.write(_fresh())

    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    assert len(arq_pool.calls) == 1
    args, kwargs = arq_pool.calls[0]
    # The Story 32.4 `enqueue_recompute` plumbing — NOT re-derived here: job name, the
    # (stl_hash, bundle_hash) 2-tuple payload, the deterministic _job_id, and the queue name.
    assert args == (SLICE_JOB_NAME, STL_HASH, BUNDLE_HASH)
    assert kwargs["_job_id"] == slice_job_id(STL_HASH, BUNDLE_HASH)
    assert kwargs["_queue_name"] == SLICER_QUEUE_NAME


@pytest.mark.asyncio
async def test_recompute_response_carries_no_internal_field_names(recompute_seam):
    ac, store, _resolver, _arq_pool = recompute_seam
    store.write(_fresh())
    ac.cookies.set("portal_access", _member_cookie())
    r = await ac.post("/api/estimates/recompute", json=_recompute_body())
    assert r.status_code == 200
    raw = r.text
    for internal in (
        "settings_ids",
        "bundle_hash",
        "stl_hash",
        "job_id",
        "_job_id",
        "_queue_name",
        "source_snapshot_ref",
        "spoolman_overrides_ref",
        "filament_max_volumetric_speed",
        "gcode",
    ):
        assert internal not in raw, f"internal field {internal!r} leaked into the response body"
