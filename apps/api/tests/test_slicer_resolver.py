"""Tests for the Orca profile resolver subsystem (Story 32.1, Initiative 20).

Covers the actual story contract (Decision AH): recursive inheritance merge with
user-partial-wins, CLI normalization (inject ``type`` / drop ``instantiation``),
deterministic ``bundle_hash`` over machine ∥ process ∥ filament ∥ orca_version,
resolver precedence with classified failures, the Spoolman override seam, the
CLI-validator seam, forward-compat (full process JSON), the settings slot, and
the no-Fenrir/no-/mnt/c grep invariant.

The merge/hash/precedence core is pure and unit-tested against the checked-in
fixtures under ``tests/fixtures/slicer/``; the validator + override layers are
interface-first with injected fakes (no real Orca binary required).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.merge import (
    InvalidPartialError,
    MissingSystemProfileError,
    normalize_for_cli,
    resolve_inheritance,
)
from app.modules.slicer.models import (
    FilamentOverrides,
    PrintIntentPreset,
    ResolvedTriple,
    ResolveFailure,
    ResolveReason,
    ResolveSuccess,
)
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.profile_offer import ProfileChain
from app.modules.slicer.profile_policy import (
    EstimateProfileSource,
    MaterialDefault,
    ProfilePolicy,
    ProfileSelection,
)
from app.modules.slicer.resolver import (
    VendoredProfileSource,
    compute_bundle_hash,
    resolve,
    resolve_chain,
)
from app.modules.slicer.validation import NullCliValidator, ValidationResult, check_required_keys

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

PLA_INTENT = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)
TPU_INTENT = PrintIntentPreset(
    name="TPU standard",
    material_class="TPU",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)
UNSUPPORTED_INTENT = PrintIntentPreset(
    name="PETG default",
    material_class="PETG",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)


# --- Test fakes (no real Orca, no real Spoolman) --------------------------------


class _FailingValidator:
    def __init__(self) -> None:
        self.calls = 0

    def validate(self, triple: ResolvedTriple) -> ValidationResult:
        self.calls += 1
        return ValidationResult(ok=False, reason="orca exited 1")


class _CountingNullValidator:
    def __init__(self) -> None:
        self.calls = 0

    def validate(self, triple: ResolvedTriple) -> ValidationResult:
        self.calls += 1
        return ValidationResult(ok=True)


class _FixedOverrideProvider:
    def __init__(self, overrides: FilamentOverrides | None) -> None:
        self._overrides = overrides

    def overrides_for(self, intent: PrintIntentPreset) -> FilamentOverrides | None:
        return self._overrides


def _resolve(intent, source, store, *, overrides=None, validator=None, orca="2.3.2"):
    return resolve(
        intent,
        source=source,
        store=store,
        override_provider=_FixedOverrideProvider(overrides)
        if overrides is not None
        else NoopOverrideProvider(),
        validator=validator or NullCliValidator(),
        orca_version=orca,
    )


# --- AC-3: recursive inheritance merge, user partial wins -----------------------


def test_resolve_inheritance_user_partial_overrides_system_default():
    source = VendoredProfileSource(FIXTURES)
    tree = source.system_tree()
    partials = source.intent_partials(PLA_INTENT)
    # user -> "0.20mm Standard" -> "fdm_process_common" (>=2-level chain).
    merged = resolve_inheritance(tree, partials["process"])
    assert merged["wall_loops"] == "3"  # user partial wins over inherited "2"
    assert merged["layer_height"] == "0.2"  # from the system child
    assert merged["sparse_infill_density"] == "15%"  # carried from the grandparent
    assert "inherit" not in merged  # the inherit chain is fully resolved away


def test_resolve_inheritance_missing_parent_raises():
    source = VendoredProfileSource(FIXTURES)
    tree = source.system_tree()
    with pytest.raises(MissingSystemProfileError):
        resolve_inheritance(tree, {"inherit": "no-such-system-profile"})


# --- PROFILE-PUBLISH-FIX: plural `inherits` (real Orca) == singular `inherit` ----
#
# Imported real Orca USER profiles carry the PLURAL key ``inherits``; the bench/
# legacy exports carry singular ``inherit``. The merge path historically resolved
# only the singular key, so a published offer chain built from real Orca blocks
# merged NOTHING from its system parent and leaked an unresolved ``inherits`` key
# into the bundle — headless Orca then rejected it (``process not compatible with
# printer`` / RC -17) while the Windows GUI silently resolved it from its registry.


def test_resolve_inheritance_resolves_plural_inherits_like_singular():
    # The system child uses singular ``inherit`` (bench-exported tree); the user
    # partial uses plural ``inherits`` (real Orca) — exactly the live mixed chain.
    tree = {
        "0.20mm Standard @Creality": {
            "name": "0.20mm Standard @Creality",
            "inherit": "fdm_process_common",
            "from": "system",
            "layer_height": "0.2",
        },
        "fdm_process_common": {
            "name": "fdm_process_common",
            "from": "system",
            "wall_loops": "2",
            "sparse_infill_density": "15%",
        },
    }
    user_partial = {
        "name": "AI 0.20mm TPU - FlowTech",
        "from": "User",
        "inherits": "0.20mm Standard @Creality",  # PLURAL — real Orca user export
        "wall_loops": "3",  # user override must win
    }
    merged = resolve_inheritance(tree, user_partial)
    assert merged["wall_loops"] == "3"  # user partial wins over inherited "2"
    assert merged["layer_height"] == "0.2"  # materialized from the system child
    assert merged["sparse_infill_density"] == "15%"  # materialized from the grandparent
    assert "inherits" not in merged  # plural recipe key resolved away
    assert "inherit" not in merged  # singular recipe key resolved away


def test_resolve_inheritance_plural_inherits_missing_parent_raises():
    with pytest.raises(MissingSystemProfileError):
        resolve_inheritance({}, {"inherits": "no-such-system-profile"})


def test_resolve_inheritance_rejects_non_string_plural_inherits():
    # A malformed plural ``inherits`` (list/number) must classify as invalid_partial,
    # never leak a bare TypeError — mirroring the singular-key guard.
    with pytest.raises(InvalidPartialError):
        resolve_inheritance({}, {"inherits": ["A", "B"]})


# --- AC-4: normalize — inject type, drop instantiation --------------------------


@pytest.mark.parametrize("kind", ["machine", "process", "filament"])
def test_normalize_injects_type_for_each_kind(kind):
    out = normalize_for_cli({"name": "x"}, profile_kind=kind)
    assert out["type"] == kind


def test_normalize_drops_instantiation_field():
    out = normalize_for_cli(
        {"instantiation": "true", "layer_height": "0.2"}, profile_kind="process"
    )
    assert "instantiation" not in out
    assert out["layer_height"] == "0.2"  # a slicing-relevant key survives


def test_normalize_does_not_mutate_input():
    src = {"instantiation": "true", "layer_height": "0.2"}
    snapshot = dict(src)
    normalize_for_cli(src, profile_kind="process")
    assert src == snapshot


def test_normalize_drops_plural_inherits_key():
    # Defensive: even if a plural ``inherits`` survived to normalization, it must
    # never reach the CLI-bound bundle (PROFILE-PUBLISH-FIX).
    out = normalize_for_cli(
        {"inherits": "Some Parent", "layer_height": "0.2"}, profile_kind="process"
    )
    assert "inherits" not in out
    assert out["layer_height"] == "0.2"


# --- AC-5 / AC-10: canonicalized bundle hash ------------------------------------


def test_bundle_hash_is_stable_across_cosmetic_json_churn():
    # Same semantic triple, two cosmetically-different JSON encodings
    # (reordered keys + reformatted floats) must hash identically.
    m1 = json.loads('{"a": 1, "b": 2.0}')
    m2 = json.loads('{"b": 2.000, "a": 1}')
    process = {"x": 1}
    filament = {"k": 3}
    assert compute_bundle_hash(m1, process, filament, "2.3.2") == compute_bundle_hash(
        m2, process, filament, "2.3.2"
    )


def test_bundle_hash_changes_when_a_slicing_value_changes():
    h1 = compute_bundle_hash({}, {"wall_loops": "3"}, {}, "2.3.2")
    h2 = compute_bundle_hash({}, {"wall_loops": "4"}, {}, "2.3.2")
    assert h1 != h2


def test_bundle_hash_changes_when_orca_version_changes():
    h1 = compute_bundle_hash({"a": 1}, {}, {}, "2.3.2")
    h2 = compute_bundle_hash({"a": 1}, {}, {}, "2.3.3")
    assert h1 != h2


def test_bundle_hash_input_order_is_machine_process_filament():
    a = {"slot": "A"}
    b = {"slot": "B"}
    # Swapping two equal-shaped JSONs across the machine/process slots must change
    # the hash — guards against a silent concatenation-order regression.
    assert compute_bundle_hash(a, b, {}, "v") != compute_bundle_hash(b, a, {}, "v")


def test_bundle_hash_is_sha256_hex():
    digest = compute_bundle_hash({"a": 1}, {}, {}, "2.3.2")
    assert isinstance(digest, str)
    assert len(digest) == 64
    int(digest, 16)


# --- AC-13: determinism ---------------------------------------------------------


def test_bundle_hash_deterministic_across_100_calls():
    hashes = {compute_bundle_hash({"a": 1}, {"b": 2}, {"c": 3.0}, "2.3.2") for _ in range(100)}
    assert len(hashes) == 1


# --- AC-7: resolver precedence + classified failure -----------------------------


def test_resolve_falls_through_to_material_default_when_no_exact_bundle(tmp_path):
    store = BundleStore(tmp_path)
    out = _resolve(PLA_INTENT, VendoredProfileSource(FIXTURES), store)
    assert isinstance(out, ResolveSuccess)
    assert out.from_cache is False
    assert store.has_bundle(out.bundle.bundle_hash)
    expected = json.loads((FIXTURES / "expected" / "pla_standard_triple.json").read_text())
    assert out.triple.machine == expected["machine"]
    assert out.triple.process == expected["process"]
    assert out.triple.filament == expected["filament"]


def test_resolve_prefers_exact_bundle_when_present(tmp_path):
    store = BundleStore(tmp_path)
    src = VendoredProfileSource(FIXTURES)
    first = _resolve(PLA_INTENT, src, store)
    assert isinstance(first, ResolveSuccess)
    # A second resolve with a validator that WOULD fail must still return the
    # pre-resolved (exact) bundle without re-validating — exact-bundle precedence.
    failing = _FailingValidator()
    second = _resolve(PLA_INTENT, src, store, validator=failing)
    assert isinstance(second, ResolveSuccess)
    assert second.from_cache is True
    assert second.bundle.bundle_hash == first.bundle.bundle_hash
    assert failing.calls == 0


def test_resolve_unsupported_material_class_yields_classified_failure(tmp_path):
    store = BundleStore(tmp_path)
    out = _resolve(UNSUPPORTED_INTENT, VendoredProfileSource(FIXTURES), store)
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.unsupported_material_class
    # No silent fallback to a default and NO bundle file written.
    assert list(tmp_path.rglob("*.json")) == []


def test_resolve_invalid_partial_yields_classified_failure(tmp_path):
    # A TPU intent whose filament partial omits the required
    # filament_max_volumetric_speed must classify as invalid_partial.
    root = tmp_path / "vend"
    (root / "system").mkdir(parents=True)
    (root / "system" / "flex.json").write_text(
        json.dumps(
            {
                "name": "FlexNoVMS",
                "from": "system",
                "instantiation": "true",
                "filament_type": ["TPU"],
                "nozzle_temperature": ["225"],
            }
        )
    )
    (root / "system" / "mach.json").write_text(
        json.dumps({"name": "M", "from": "system", "instantiation": "true"})
    )
    (root / "system" / "proc.json").write_text(
        json.dumps({"name": "P", "from": "system", "instantiation": "true", "layer_height": "0.2"})
    )
    idir = root / "intents" / "px" / "TPU"
    idir.mkdir(parents=True)
    (idir / "standard.json").write_text(
        json.dumps(
            {
                "machine": {"inherit": "M"},
                "process": {"inherit": "P"},
                "filament": {"inherit": "FlexNoVMS"},
            }
        )
    )
    intent = PrintIntentPreset(
        name="broken tpu", material_class="TPU", quality_tier="standard", printer_ref="px"
    )
    store = BundleStore(tmp_path / "store")
    out = _resolve(intent, VendoredProfileSource(root), store)
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.invalid_partial
    assert list((tmp_path / "store").rglob("*.json")) == []


def test_resolve_missing_system_profile_yields_classified_failure(tmp_path):
    root = tmp_path / "vend"
    (root / "system").mkdir(parents=True)
    (root / "system" / "m.json").write_text(
        json.dumps({"name": "M", "from": "system", "instantiation": "true"})
    )
    idir = root / "intents" / "px" / "PLA"
    idir.mkdir(parents=True)
    (idir / "standard.json").write_text(
        json.dumps(
            {
                "machine": {"inherit": "DOES_NOT_EXIST"},
                "process": {"inherit": "M"},
                "filament": {"inherit": "M"},
            }
        )
    )
    intent = PrintIntentPreset(
        name="missing", material_class="PLA", quality_tier="standard", printer_ref="px"
    )
    out = _resolve(intent, VendoredProfileSource(root), BundleStore(tmp_path / "s"))
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.missing_system_profile


# --- AC-9: CLI-validator seam ---------------------------------------------------


def test_resolver_calls_validator_before_persisting(tmp_path):
    store = BundleStore(tmp_path)
    failing = _FailingValidator()
    out = _resolve(PLA_INTENT, VendoredProfileSource(FIXTURES), store, validator=failing)
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.cli_validation_failed
    assert failing.calls == 1
    assert list(tmp_path.rglob("*.json")) == []  # nothing persisted on validation failure


def test_null_validator_implements_interface():
    from app.modules.slicer.validation import CliValidator

    validator = NullCliValidator()
    assert isinstance(validator, CliValidator)
    assert validator.validate(ResolvedTriple(machine={}, process={}, filament={})).ok is True


def test_required_key_schema_assertion_tpu_volumetric_speed(tmp_path):
    # A valid TPU triple (fixture carries the key) resolves clean.
    out = _resolve(TPU_INTENT, VendoredProfileSource(FIXTURES), BundleStore(tmp_path))
    assert isinstance(out, ResolveSuccess)
    # The schema helper rejects a TPU filament missing the required key.
    bad = ResolvedTriple(machine={}, process={}, filament={"filament_type": ["TPU"]})
    res = check_required_keys(bad, "TPU")
    assert res.ok is False


def test_orca_smoke_command_template_is_specified():
    from app.modules.slicer.validation import ORCA_SMOKE_COMMAND_TEMPLATE

    assert "--load-settings" in ORCA_SMOKE_COMMAND_TEMPLATE
    assert "--load-filaments" in ORCA_SMOKE_COMMAND_TEMPLATE


@pytest.mark.skipif(
    os.environ.get("ORCA_SMOKE_TEST") != "1",
    reason="bench-only: requires the real Orca AppImage (set ORCA_SMOKE_TEST=1)",
)
def test_resolved_triple_accepted_by_orca_cli_smoke(tmp_path):  # pragma: no cover
    import subprocess

    from app.modules.slicer.validation import build_orca_smoke_command

    out = _resolve(PLA_INTENT, VendoredProfileSource(FIXTURES), BundleStore(tmp_path))
    assert isinstance(out, ResolveSuccess)
    machine = tmp_path / "machine.json"
    process = tmp_path / "process.json"
    filament = tmp_path / "filament.json"
    machine.write_text(json.dumps(out.triple.machine))
    process.write_text(json.dumps(out.triple.process))
    filament.write_text(json.dumps(out.triple.filament))
    probe = tmp_path / "probe.stl"
    probe.write_bytes(b"solid x\nendsolid x\n")
    cmd = build_orca_smoke_command(machine, process, filament, probe)
    result = subprocess.run(cmd, capture_output=True)
    assert result.returncode == 0


# --- AC-8: Spoolman override-layer seam -----------------------------------------


def test_resolver_uses_injected_override_provider(tmp_path):
    src = VendoredProfileSource(FIXTURES)
    noop_out = _resolve(PLA_INTENT, src, BundleStore(tmp_path / "a"))
    ov = FilamentOverrides(filament_max_volumetric_speed=8.0)
    ov_out = _resolve(PLA_INTENT, src, BundleStore(tmp_path / "b"), overrides=ov)
    assert isinstance(ov_out, ResolveSuccess)
    assert ov_out.triple.filament["filament_max_volumetric_speed"] == ["8.0"]
    assert ov_out.bundle.bundle_hash != noop_out.bundle.bundle_hash
    assert ov_out.bundle.spoolman_overrides_ref is not None


def test_noop_provider_yields_override_free_bundle(tmp_path):
    out = _resolve(PLA_INTENT, VendoredProfileSource(FIXTURES), BundleStore(tmp_path))
    assert isinstance(out, ResolveSuccess)
    assert out.bundle.spoolman_overrides_ref is None


# --- AC-11: forward-compat — full process JSON preserved ------------------------


def test_bundle_preserves_full_process_json_not_a_flattened_layer_height(tmp_path):
    out = _resolve(PLA_INTENT, VendoredProfileSource(FIXTURES), BundleStore(tmp_path))
    assert isinstance(out, ResolveSuccess)
    proc = out.bundle.process
    assert isinstance(proc, dict)
    # Full process JSON retained, NOT collapsed to a single scalar layer height —
    # keeps a later variable/adaptive-height bundle representable.
    assert "wall_loops" in proc
    assert "sparse_infill_density" in proc
    assert "adaptive_layer_height" in proc


# --- AC-12: settings slot drives the vendored-artifact location -----------------


def test_resolver_reads_vendored_artifacts_from_settings_not_hardcoded_path(tmp_path, monkeypatch):
    from app.core import config as config_mod
    from app.modules.slicer.resolver import resolve_intent

    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(FIXTURES))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("ORCA_VERSION", "2.3.2")
    config_mod.get_settings.cache_clear()
    try:
        out = resolve_intent(PLA_INTENT)
        assert isinstance(out, ResolveSuccess)
        assert (tmp_path / "store" / "bundles").exists()
    finally:
        config_mod.get_settings.cache_clear()


def test_no_fenrir_or_mnt_c_literal_in_slicer_module():
    import app.modules.slicer as pkg

    pkg_dir = Path(pkg.__file__).parent
    pattern = re.compile(r"/mnt/c|fenrir", re.IGNORECASE)
    # AC-12 invariant is over the WHOLE module dir (code + README), not just *.py.
    offenders = [
        str(f)
        for f in pkg_dir.rglob("*")
        if f.is_file()
        and f.suffix != ".pyc"
        and "__pycache__" not in f.parts
        and pattern.search(f.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert offenders == [], f"Fenrir/`/mnt/c` literal leaked into: {offenders}"


# --- Review fix #1: override fingerprint folded into bundle_hash -----------------


def test_bundle_hash_folds_override_fingerprint():
    # Same resolved triple + orca_version but a different override fingerprint MUST
    # yield a different hash — otherwise an override whose APPLIED values equal the
    # material-class default (a no-op on the filament JSON) collides with the true
    # no-override bundle and the exact-cache branch silently drops the override
    # provenance (``spoolman_overrides_ref``).
    base = compute_bundle_hash({"a": 1}, {}, {"f": 1}, "2.3.2")
    with_ref = compute_bundle_hash({"a": 1}, {}, {"f": 1}, "2.3.2", overrides_ref="deadbeef")
    other_ref = compute_bundle_hash({"a": 1}, {}, {"f": 1}, "2.3.2", overrides_ref="feedface")
    assert base != with_ref
    assert with_ref != other_ref
    # No-override (None) stays byte-identical to the legacy 4-part key.
    assert compute_bundle_hash({"a": 1}, {}, {"f": 1}, "2.3.2", overrides_ref=None) == base


def test_resolve_override_equal_to_default_is_distinct_from_noop(tmp_path):
    # An override whose APPLIED values equal the PLA default filament
    # (nozzle_temperature 210 / hot_plate_temp 60 — see
    # fixtures/expected/pla_standard_triple.json) is a no-op on the filament JSON,
    # yet must NOT collide with the no-override bundle: the override bundle carries
    # ``spoolman_overrides_ref`` provenance, the no-op one does not.
    src = VendoredProfileSource(FIXTURES)
    store = BundleStore(tmp_path)
    noop = _resolve(PLA_INTENT, src, store)
    assert isinstance(noop, ResolveSuccess)
    assert noop.bundle.spoolman_overrides_ref is None

    equal_to_default = FilamentOverrides(nozzle_temperature=210, hot_plate_temp=60)
    ov = _resolve(PLA_INTENT, src, store, overrides=equal_to_default)
    assert isinstance(ov, ResolveSuccess)
    # Applied override leaves the filament JSON byte-identical to the default...
    assert ov.triple.filament == noop.triple.filament
    # ...but the bundle is a DISTINCT, provenance-carrying record (not a cache hit).
    assert ov.from_cache is False
    assert ov.bundle.bundle_hash != noop.bundle.bundle_hash
    assert ov.bundle.spoolman_overrides_ref is not None


# --- Review fix #2: malformed intent partial → invalid_partial (not KeyError) ----


def _write_min_system(root: Path) -> None:
    (root / "system").mkdir(parents=True, exist_ok=True)
    for name in ("M", "P", "F"):
        (root / "system" / f"{name}.json").write_text(
            json.dumps({"name": name, "from": "system", "instantiation": "true"})
        )


@pytest.mark.parametrize(
    "partial_body",
    [
        {"machine": {"inherit": "M"}, "process": {"inherit": "P"}},  # missing filament
        {"process": {"inherit": "P"}, "filament": {"inherit": "F"}},  # missing machine
        {"machine": {"inherit": "M"}, "filament": {"inherit": "F"}},  # missing process
        {"machine": "M", "process": {"inherit": "P"}, "filament": {"inherit": "F"}},  # wrong shape
        # inherit of the wrong TYPE (a list, not a system-profile name string): the
        # entry is a dict so it clears the shape gate, but the merge would otherwise
        # raise a bare ``TypeError: unhashable type: list`` instead of classifying.
        {
            "machine": {"inherit": ["M"]},
            "process": {"inherit": "P"},
            "filament": {"inherit": "F"},
        },
        ["machine", "process", "filament"],  # not even a JSON object
    ],
)
def test_resolve_malformed_partial_yields_invalid_partial(tmp_path, partial_body):
    # A vendored intent partial missing a machine/process/filament entry (or with a
    # non-dict entry, or that is not an object at all) must classify as
    # ``invalid_partial`` — never surface a bare KeyError/AttributeError.
    root = tmp_path / "vend"
    _write_min_system(root)
    idir = root / "intents" / "px" / "PLA"
    idir.mkdir(parents=True)
    (idir / "standard.json").write_text(json.dumps(partial_body))
    intent = PrintIntentPreset(
        name="malformed", material_class="PLA", quality_tier="standard", printer_ref="px"
    )
    out = _resolve(intent, VendoredProfileSource(root), BundleStore(tmp_path / "store"))
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.invalid_partial
    assert list((tmp_path / "store").rglob("*.json")) == []  # nothing persisted


# --- Story 35.6: resolve_chain(..., profile_selection=...) (AC-12) ----------------


def _write_chain_tree(root: Path) -> tuple[Path, ProfileChain]:
    """Write a minimal vendored tree with library blocks + system profiles.

    Returns (root, chain) where chain references the three library block IDs.
    Two filament system profiles: ``Generic PLA`` (210 °C) and ``PLA Matt`` (215 °C).
    """
    sysd = root / "system"
    sysd.mkdir(parents=True, exist_ok=True)
    for body in [
        {"name": "fdm_filament_common", "from": "system", "instantiation": "false",
         "filament_flow_ratio": ["0.98"]},
        {"name": "M", "from": "system", "instantiation": "true"},
        {"name": "P", "from": "system", "instantiation": "true", "layer_height": "0.2"},
        {"name": "Generic PLA", "inherit": "fdm_filament_common", "from": "system",
         "instantiation": "true", "filament_type": ["PLA"], "nozzle_temperature": ["210"]},
        {"name": "PLA Matt", "inherit": "fdm_filament_common", "from": "system",
         "instantiation": "true", "filament_type": ["PLA"], "nozzle_temperature": ["215"]},
    ]:
        (sysd / f"{body['name'].lower().replace(' ', '_')}.json").write_text(json.dumps(body))
    # Write machine/process/filament blocks under library/
    lib = root / "library"
    machine_id = "mach-001"
    process_id = "proc-001"
    filament_id = "fil-001"
    (lib / "machine").mkdir(parents=True, exist_ok=True)
    (lib / "process").mkdir(parents=True, exist_ok=True)
    (lib / "filament").mkdir(parents=True, exist_ok=True)
    (lib / "machine" / f"{machine_id}.json").write_text(
        json.dumps({"inherit": "M"})
    )
    (lib / "process" / f"{process_id}.json").write_text(
        json.dumps({"inherit": "P"})
    )
    (lib / "filament" / f"{filament_id}.json").write_text(
        json.dumps({"inherit": "Generic PLA"})
    )
    chain = ProfileChain(
        machine_block_id=machine_id,
        process_block_id=process_id,
        filament_block_id=filament_id,
    )
    return root, chain


def test_resolve_chain_no_profile_selection_byte_identical(tmp_path):
    """resolve_chain(profile_selection=None) must be byte-identical to the base call (AC-12)."""
    root, chain = _write_chain_tree(tmp_path / "vend")
    src = VendoredProfileSource(root)
    store_a = BundleStore(tmp_path / "a")
    store_b = BundleStore(tmp_path / "b")

    base = resolve_chain(
        chain,
        source=src,
        store=store_a,
        validator=NullCliValidator(),
        orca_version="2.3.2",
        material_class="PLA",
    )
    with_none = resolve_chain(
        chain,
        source=src,
        store=store_b,
        validator=NullCliValidator(),
        orca_version="2.3.2",
        material_class="PLA",
        profile_selection=None,
    )
    assert isinstance(base, ResolveSuccess)
    assert isinstance(with_none, ResolveSuccess)
    assert with_none.bundle.bundle_hash == base.bundle.bundle_hash
    assert with_none.profile_selection is None


def test_resolve_chain_default_material_profile_selection_succeeds(tmp_path):
    """resolve_chain with default_material_profile selection substitutes the filament (AC-12)."""
    root, chain = _write_chain_tree(tmp_path / "vend")
    src = VendoredProfileSource(root)
    store = BundleStore(tmp_path / "store")

    selection = ProfileSelection(
        source=EstimateProfileSource.default_material_profile,
        orca_filament_profile_ref="PLA Matt",
        selected_material="PLA",
    )
    out = resolve_chain(
        chain,
        source=src,
        store=store,
        validator=NullCliValidator(),
        orca_version="2.3.2",
        material_class="PLA",
        profile_selection=selection,
    )
    assert isinstance(out, ResolveSuccess)
    assert out.profile_selection == selection
    # The PLA Matt profile (215 °C) is different from the default Generic PLA (210 °C),
    # so the bundle_hash must differ from the no-selection base resolve.
    store_base = BundleStore(tmp_path / "base")
    base = resolve_chain(
        chain,
        source=src,
        store=store_base,
        validator=NullCliValidator(),
        orca_version="2.3.2",
        material_class="PLA",
    )
    assert isinstance(base, ResolveSuccess)
    assert out.bundle.bundle_hash != base.bundle.bundle_hash


def test_resolve_chain_unavailable_no_profile_returns_failure_early(tmp_path):
    """resolve_chain with unavailable_no_profile must return ResolveFailure without writing (AC-12)."""
    root, chain = _write_chain_tree(tmp_path / "vend")
    src = VendoredProfileSource(root)
    store = BundleStore(tmp_path / "store")

    selection = ProfileSelection(
        source=EstimateProfileSource.unavailable_no_profile,
        orca_filament_profile_ref=None,
        selected_material="UNKNOWN",
    )
    out = resolve_chain(
        chain,
        source=src,
        store=store,
        validator=NullCliValidator(),
        orca_version="2.3.2",
        material_class="PLA",
        profile_selection=selection,
    )
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.unavailable_no_profile
    # Nothing must have been written to the bundle store.
    assert list(store._root.rglob("*.json")) == []
