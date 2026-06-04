"""Profile-resolver orchestration: read → merge → normalize → override → validate
→ hash → snapshot/persist (Story 32.1, Decision AH).

The hash path (:func:`compute_bundle_hash`) is pure and deterministic — no clock,
no randomness — so identical inputs always produce identical bytes and the same
hash across processes and restarts (NFR20-DETERMINISM-1). The only non-pure step
is persistence + the ``created_at`` stamp, which is deliberately EXCLUDED from the
hash.

[Source: architecture.md § Decision AH; realizes FR20-RESOLVER-1]
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.core.config import get_settings
from app.modules.slicer.attribution_store import AttributionSink, AttributionStore
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.merge import (
    InvalidPartialError,
    MissingSystemProfileError,
    normalize_for_cli,
    resolve_inheritance,
)
from app.modules.slicer.models import (
    PrintIntentPreset,
    ResolvedTriple,
    ResolveFailure,
    ResolveOutcome,
    ResolveReason,
    ResolveSuccess,
    SlicerProfileBundle,
    SourceProfileSnapshot,
)
from app.modules.slicer.overrides import (
    NoopOverrideProvider,
    OverrideProvider,
    apply_filament_overrides,
    overrides_fingerprint,
)
from app.modules.slicer.validation import (
    CliValidator,
    NullCliValidator,
    check_required_keys,
)

# Resolver-logic version: provenance constant, bumped when the merge/normalize
# logic changes so an old SourceProfileSnapshot is diffable against a re-resolve
# (AC-6/AC-10). NOT folded into bundle_hash (the resolved JSONs already capture
# the output); it records *how* a bundle was produced.
RESOLVER_VERSION: Final = "1"

# Content-addressed bundle identity: sha256 gives collision-resistance over a
# tiny JSON corpus — Decision AH (AC-10).
_HASH_ALGORITHM: Final = "sha256"


def _canonical_json(obj: dict) -> str:
    """Deterministic canonical JSON: sorted keys, no whitespace.

    Cosmetic JSON churn must NOT churn the hash (FR20-RESOLVER-1, AC-5):
    ``sort_keys`` absorbs key reordering; ``json.dumps`` renders floats via a
    stable repr so ``1.0`` and ``1.00`` (which parse to the same float) both
    serialize to ``1.0``. ``ensure_ascii=False`` keeps unicode stable.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_bundle_hash(
    machine: dict,
    process: dict,
    filament: dict,
    orca_version: str,
    overrides_ref: str | None = None,
) -> str:
    """Canonicalized ``bundle_hash`` over machine ∥ process ∥ filament ∥ orca_version
    ∥ overrides_ref.

    The concatenation order ``machine ∥ process ∥ filament ∥ orca_version`` is
    because "byte-pinned reproducibility-key ordering — Decision AH; reorder ⇒
    silent cache-key divergence (R9). Change requires an SCP." Each JSON is
    canonicalized (AC-5) before concatenation; ``orca_version`` is folded in last
    because "an Orca upgrade is a clean bulk-invalidation event — Decision AJ /
    NFR20-REPRODUCIBLE-1".

    ``overrides_ref`` (the Spoolman override fingerprint) is folded in AFTER
    ``orca_version`` because an override whose APPLIED values happen to equal the
    material-class default is a no-op on the filament JSON, so without it the
    override resolve would collide with the true no-override bundle and the
    exact-cache branch would return that bundle WITHOUT ``spoolman_overrides_ref``
    — silently dropping override provenance (review fix #1). It is appended ONLY
    when present, so a plain no-override hash stays byte-identical to the legacy
    4-part key (no spurious cache invalidation of already-persisted bundles).
    """
    parts = [
        _canonical_json(machine),
        _canonical_json(process),
        _canonical_json(filament),
        orca_version,
    ]
    if overrides_ref is not None:
        parts.append(overrides_ref)
    # NUL separator: an unambiguous delimiter that cannot appear in the canonical
    # JSON text, so two different slot-splits cannot collide on the same byte run.
    payload = "\x00".join(parts).encode("utf-8")
    return hashlib.new(_HASH_ALGORITHM, payload).hexdigest()


class VendoredProfileSource:
    """Reads the vendored Orca system tree + user partials from a root directory.

    The production root is the settings slot (AC-10/AC-12), defaulting to a
    container-internal path; these are vendored/exported artifacts — a one-time
    snapshot from the bench, NEVER a live read of an external host at resolve time
    (Decision AH § 1). Layout::

        <root>/system/*.json                         # system profiles, keyed by "name"
        <root>/intents/<printer_ref>/<material_class>/<quality_tier>.json
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def system_tree(self) -> dict[str, dict]:
        """Load every system profile, keyed by its Orca ``name`` field."""
        tree: dict[str, dict] = {}
        system_dir = self._root / "system"
        if not system_dir.exists():
            return tree
        for path in sorted(system_dir.glob("*.json")):
            profile = json.loads(path.read_text(encoding="utf-8"))
            tree[profile["name"]] = profile
        return tree

    def intent_path(self, intent: PrintIntentPreset) -> Path:
        """The on-disk path of the vendored intent-triple file for ``intent``.

        Single source of the ``<root>/intents/<printer_ref>/<material_class>/
        <quality_tier>.json`` layout (Decision AH § 1) so existence checks and reads
        cannot drift from each other.
        """
        return (
            self._root
            / "intents"
            / intent.printer_ref
            / intent.material_class
            / f"{intent.quality_tier}.json"
        )

    def has_intent(self, intent: PrintIntentPreset) -> bool:
        """True when the vendored intent-triple file EXISTS (Story 33.1 ``imported``).

        Pure file-existence — it does NOT parse. A present-but-malformed file therefore
        reports ``imported=true`` while still being ``resolvable=false`` (the inventory's
        import-vs-resolve distinction, AC-5). Read-only.
        """
        return self.intent_path(intent).exists()

    def system_tree_hash(self) -> str:
        """Content hash of the vendored system-profile tree (Story 33.1 provenance).

        The SAME ``source_system_tree_hash`` value :func:`resolve` persists into the
        provenance snapshot (resolver.py snapshot ``source_system_tree_hash``) — reused
        here as a read-only projection so the admin inventory can surface provenance
        without re-resolving or reading persisted snapshots. Read-only.
        """
        return _content_hash(self.system_tree())

    def intent_partials(self, intent: PrintIntentPreset) -> dict | None:
        """Return the {machine, process, filament} user partials for ``intent``.

        ``None`` when no vendored intent exists for the material class — the
        resolver maps that to the classified ``unsupported_material_class``.
        """
        path = self.intent_path(intent)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


def _now_iso() -> str:
    """Provenance timestamp. Excluded from every content hash, so non-pure-but-safe."""
    return datetime.now(UTC).isoformat()


def _content_hash(payload: dict) -> str:
    return hashlib.new(_HASH_ALGORITHM, _canonical_json(payload).encode("utf-8")).hexdigest()


def _record_attribution(
    attribution_sink: AttributionSink | None,
    intent: PrintIntentPreset,
    bundle_hash: str,
) -> None:
    """SPOOL-PREQ-1 reverse-index write — DI-clean, non-breaking by default.

    Records ``(spoolman_filament_ref, intent, bundle_hash)`` so a future Spoolman
    filament change (SPOOL-EVT-1) can map the ref back to the affected estimate keys.
    A ``None`` sink (the default — today's behavior) OR an intent with no usable pin is a
    byte-identical no-op: resolve output is unchanged. "No usable pin" is any FALSY ref —
    ``None`` and the empty string alike — so a degenerate ``spoolman_filament_ref=""`` pin
    (the field has no non-blank validator) never creates a meaningless index bucket. Fired
    on BOTH success branches (fresh persist AND exact-bundle cache hit), because a cache hit
    is still a real pin of that ref to that bundle.
    """
    if attribution_sink is None or not intent.spoolman_filament_ref:
        return
    attribution_sink.record(intent.spoolman_filament_ref, intent, bundle_hash)


def resolve(
    intent: PrintIntentPreset,
    *,
    source: VendoredProfileSource,
    store: BundleStore,
    override_provider: OverrideProvider,
    validator: CliValidator,
    orca_version: str,
    attribution_sink: AttributionSink | None = None,
) -> ResolveOutcome:
    """Resolve ``intent`` to a persisted bundle, or a classified failure (AC-7).

    Precedence (load-bearing contract): ``exact bundle > custom override >
    material-class default > unsupported``. Implemented as:

    1. **unsupported** — no vendored intent for the material class ⇒
       ``unsupported_material_class`` (no file written).
    2. build the triple from the **material-class default** partials (inheritance
       merge + CLI normalize), then apply the **custom override** layer onto the
       filament before hashing.
    3. **exact bundle** — if a bundle already exists at the computed content hash,
       return it directly (idempotent; skips re-validation + re-persist).
    4. otherwise validate (required-key schema ⇒ ``invalid_partial``; CLI smoke ⇒
       ``cli_validation_failed``) then persist append-only and return success.

    ``attribution_sink`` (SPOOL-PREQ-1) is an OPTIONAL reverse-index write seam mirroring
    ``override_provider``: on a SUCCESSFUL resolve whose intent pins a
    ``spoolman_filament_ref`` it records ``(ref, intent, bundle_hash)``. ``None`` (the
    default) ⇒ byte-identical no-op, so every existing caller is unaffected.
    """
    # (1) unsupported material class — fail loud, before any hashing/writing.
    partials = source.intent_partials(intent)
    if partials is None:
        return ResolveFailure(
            reason=ResolveReason.unsupported_material_class,
            message=(
                f"no vendored profile for material_class={intent.material_class!r} "
                f"printer_ref={intent.printer_ref!r} quality_tier={intent.quality_tier!r}"
            ),
        )

    # (1b) malformed-partial shape gate (review fix #2): a vendored intent file must
    # be an object carrying a dict {machine, process, filament}. A missing entry or a
    # non-dict entry classifies as ``invalid_partial`` — never a bare
    # KeyError/TypeError/AttributeError leaking out of the merge below.
    _required_kinds = ("machine", "process", "filament")
    if not isinstance(partials, dict) or any(
        not isinstance(partials.get(kind), dict) for kind in _required_kinds
    ):
        return ResolveFailure(
            reason=ResolveReason.invalid_partial,
            message=(
                "vendored intent partial is malformed: expected an object with dict "
                f"{_required_kinds} entries"
            ),
        )

    # (2) material-class default resolve: inheritance merge + CLI normalize.
    system_tree = source.system_tree()
    try:
        machine = normalize_for_cli(
            resolve_inheritance(system_tree, partials["machine"]), profile_kind="machine"
        )
        process = normalize_for_cli(
            resolve_inheritance(system_tree, partials["process"]), profile_kind="process"
        )
        filament = normalize_for_cli(
            resolve_inheritance(system_tree, partials["filament"]), profile_kind="filament"
        )
    except InvalidPartialError as exc:
        return ResolveFailure(reason=ResolveReason.invalid_partial, message=str(exc))
    except MissingSystemProfileError as exc:
        return ResolveFailure(reason=ResolveReason.missing_system_profile, message=str(exc))

    # (2b) custom-override layer onto the filament BEFORE hashing (AC-8); folded
    # into the bundle via spoolman_overrides_ref so a mapped-field change re-hashes.
    overrides = override_provider.overrides_for(intent)
    overrides_ref: str | None = None
    if overrides is not None:
        filament = apply_filament_overrides(filament, overrides)
        overrides_ref = overrides_fingerprint(overrides)

    triple = ResolvedTriple(machine=machine, process=process, filament=filament)
    bundle_hash = compute_bundle_hash(
        machine, process, filament, orca_version, overrides_ref=overrides_ref
    )

    # (3) exact bundle precedence — content hit short-circuits before validation.
    existing = store.load_bundle(bundle_hash)
    if existing is not None:
        _record_attribution(attribution_sink, intent, existing.bundle_hash)
        return ResolveSuccess(bundle=existing, triple=triple, from_cache=True)

    # (4a) required-key schema assertion ⇒ invalid_partial.
    key_check = check_required_keys(triple, intent.material_class)
    if not key_check.ok:
        return ResolveFailure(
            reason=ResolveReason.invalid_partial, message=key_check.reason or "invalid partial"
        )

    # (4b) CLI-acceptance smoke ⇒ cli_validation_failed (no bundle persisted).
    cli_result = validator.validate(triple)
    if not cli_result.ok:
        return ResolveFailure(
            reason=ResolveReason.cli_validation_failed,
            message=cli_result.reason or "CLI validation failed",
        )

    # (4c) persist provenance snapshot + append-only bundle.
    # The snapshot binds the CONTENT identity of the vendored system tree
    # (``source_system_tree_hash``), not just its root path (review fix #3): the
    # vendored profiles are edited IN PLACE, so an unchanged root path would
    # otherwise collide an old snapshot with a re-resolve against mutated system
    # profiles, breaking the reproducibility-diff (AC-6).
    source_user_partial_hash = _content_hash(partials)
    snapshot_payload = {
        "source_system_tree_ref": str(source.root),
        "source_system_tree_hash": _content_hash(system_tree),
        "source_user_partial_hash": source_user_partial_hash,
        "orca_version": orca_version,
        "resolver_version": RESOLVER_VERSION,
    }
    snapshot = SourceProfileSnapshot(
        **snapshot_payload,
        snapshot_hash=_content_hash(snapshot_payload),
        created_at=_now_iso(),
    )
    store.write_snapshot(snapshot)

    bundle = SlicerProfileBundle(
        bundle_hash=bundle_hash,
        orca_version=orca_version,
        machine=machine,
        process=process,
        filament=filament,
        source_snapshot_ref=snapshot.snapshot_hash,
        spoolman_overrides_ref=overrides_ref,
        created_at=_now_iso(),
    )
    store.write_bundle(bundle)
    _record_attribution(attribution_sink, intent, bundle.bundle_hash)
    return ResolveSuccess(bundle=bundle, triple=triple, from_cache=False)


def resolve_intent(
    intent: PrintIntentPreset,
    *,
    override_provider: OverrideProvider | None = None,
    validator: CliValidator | None = None,
    attribution_sink: AttributionSink | None = None,
) -> ResolveOutcome:
    """Settings-wired convenience entry point (AC-12).

    Reads the vendored-artifact root, bundle-store root, and ``orca_version`` from
    settings — NEVER a hard-coded bench path — and delegates to :func:`resolve`.
    Defaults to the no-op override provider + the null CLI validator (the real
    Spoolman-backed provider is Story 32.5; the real Orca validator is Story 32.2).

    The SPOOL-PREQ-1 ``attribution_sink`` defaults to a real settings-wired
    ``AttributionStore`` (sharing the bundle-store content root, owning the
    ``attribution/`` subtree) so the reverse index is populated wherever the convenience
    entry point resolves. Pass ``NoopAttributionSink()`` to disable, or inject a
    test/tmp store. The write is a sidecar only — it never perturbs the resolve output.
    """
    settings = get_settings()
    return resolve(
        intent,
        source=VendoredProfileSource(settings.slicer_vendored_profiles_dir),
        store=BundleStore(settings.slicer_bundle_store_dir),
        override_provider=override_provider or NoopOverrideProvider(),
        validator=validator or NullCliValidator(),
        orca_version=settings.orca_version,
        attribution_sink=attribution_sink or AttributionStore(settings.slicer_bundle_store_dir),
    )
