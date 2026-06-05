"""Story 33.2 (T2/T3) — unit tests for the validated-import service.

Covers the two pure-ish engine pieces the import endpoint composes:

- ``StagedProfileSource`` + ``validate_import`` — reuse ``resolve()`` VERBATIM against the
  REAL vendored system tree while feeding the uploaded partials from memory, so validation
  never writes the live ``intent_path`` and never touches the append-only bundle store
  (AC-7, AC-11 validation-path-no-write).
- ``publish_intent`` + the sidecar manifest — atomic tmp→rename publish of the uploaded
  partials + a v1 manifest sibling (AC-8, AC-9); upsert overwrite-in-place; the manifest is
  a point-in-time record, NOT the live compat SoT (AC-10).

The fixtures are REAL bench-derived Orca profiles (``Rosa3D Flex 96A`` = the operator's
"Rosa Flex" TPU direction, ``Rosa3D PLA Starter``), NOT synthesized triples (G2).
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from app.modules.slicer import import_service
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.import_service import (
    MANIFEST_VERSION,
    StagedProfileSource,
    build_manifest,
    is_safe_printer_ref,
    is_valid_triple_shape,
    is_within_intents_root,
    manifest_path_for,
    publish_intent,
    read_manifest_label,
    validate_import,
)
from app.modules.slicer.models import PrintIntentPreset, ResolveFailure, ResolveSuccess
from app.modules.slicer.resolver import VendoredProfileSource

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"
PRINTER_REF = "creality-k1-max-microswiss-hf"
ORCA_VERSION = "2.3.2"

# Real bench-derived triples (G2): PLA·standard (Rosa3D PLA Starter) + TPU·standard
# (Rosa3D Flex 96A — the operator's "Rosa Flex").
PLA_PARTIALS = json.loads(
    (FIXTURES / "intents" / PRINTER_REF / "PLA" / "standard.json").read_text()
)
TPU_PARTIALS = json.loads(
    (FIXTURES / "intents" / PRINTER_REF / "TPU" / "standard.json").read_text()
)


def _intent(material_class: str, quality_tier: str) -> PrintIntentPreset:
    return PrintIntentPreset(
        name=f"{material_class} {quality_tier}",
        material_class=material_class,
        quality_tier=quality_tier,
        printer_ref=PRINTER_REF,
        spoolman_filament_ref=None,
    )


def _seed_system_tree(root: Path) -> None:
    """Copy ONLY the real vendored system tree into ``root`` (no intents)."""
    shutil.copytree(FIXTURES / "system", root / "system")


# === shape gate (AC-6) =======================================================


def test_is_valid_triple_shape_accepts_three_dict_kinds() -> None:
    assert is_valid_triple_shape(PLA_PARTIALS) is True
    assert is_valid_triple_shape(TPU_PARTIALS) is True


def test_is_valid_triple_shape_rejects_malformed() -> None:
    assert is_valid_triple_shape([]) is False  # not an object
    assert is_valid_triple_shape({"machine": {}, "process": {}}) is False  # missing kind
    # non-dict kind:
    assert is_valid_triple_shape({"machine": "x", "process": {}, "filament": {}}) is False


# === staged validation reuses resolve() verbatim (AC-7) ======================


def test_validate_import_succeeds_for_real_tpu_triple(tmp_path: Path) -> None:
    # The Rosa3D Flex 96A TPU·standard triple resolves against the real system tree.
    _seed_system_tree(tmp_path)
    outcome = validate_import(
        TPU_PARTIALS, _intent("TPU", "standard"), real_root=tmp_path, orca_version=ORCA_VERSION
    )
    assert isinstance(outcome, ResolveSuccess)


def test_validate_import_does_not_write_intent_path_or_bundle_store(tmp_path: Path) -> None:
    # AC-7/AC-11: validation MUST NOT publish the live intent_path and MUST NOT append to
    # the bundle store on the validation path.
    _seed_system_tree(tmp_path)
    intent = _intent("PLA", "standard")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    outcome = validate_import(PLA_PARTIALS, intent, real_root=tmp_path, orca_version=ORCA_VERSION)
    assert isinstance(outcome, ResolveSuccess)

    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after, "validation must not create any file in the vendored root"
    # No live intent file appeared.
    assert not VendoredProfileSource(tmp_path).has_intent(intent)


def test_validate_import_classifies_required_key_gap(tmp_path: Path) -> None:
    # A TPU triple whose filament drops the required filament_max_volumetric_speed →
    # classified invalid_partial (no resolve, no write).
    _seed_system_tree(tmp_path)
    # Point the TPU filament at the PLA-common base (no volumetric speed) by inlining a
    # partial that has no inherit to Rosa3D Flex 96A.
    broken = {
        "machine": {"inherit": "Creality K1 Max MicroSwiss HF"},
        "process": {"inherit": "0.20mm Standard"},
        "filament": {"inherit": "fdm_filament_common"},  # no filament_max_volumetric_speed
    }
    outcome = validate_import(
        broken, _intent("TPU", "standard"), real_root=tmp_path, orca_version=ORCA_VERSION
    )
    assert isinstance(outcome, ResolveFailure)
    assert outcome.reason.value == "invalid_partial"


def test_validate_import_classifies_missing_system_profile(tmp_path: Path) -> None:
    _seed_system_tree(tmp_path)
    bad = {
        "machine": {"inherit": "No Such Machine"},
        "process": {"inherit": "0.20mm Standard"},
        "filament": {"inherit": "Rosa3D PLA Starter"},
    }
    outcome = validate_import(
        bad, _intent("PLA", "standard"), real_root=tmp_path, orca_version=ORCA_VERSION
    )
    assert isinstance(outcome, ResolveFailure)
    assert outcome.reason.value == "missing_system_profile"


# === atomic publish + manifest (AC-8, AC-9, AC-10) ===========================


def test_publish_writes_partials_and_manifest_atomically(tmp_path: Path) -> None:
    _seed_system_tree(tmp_path)
    source = VendoredProfileSource(tmp_path)
    intent = _intent("TPU", "standard")
    intent_path = source.intent_path(intent)
    imported_by = uuid.uuid4()

    manifest = build_manifest(
        portal_label="Rosa Flex 96A",
        imported_by=imported_by,
        imported_at="2026-06-05T00:00:00+00:00",
        original_filename="tpu_standard.json",
        compatible=True,
        compat_reason=None,
        source_system_tree_hash=source.system_tree_hash(),
        orca_version=ORCA_VERSION,
    )
    publish_intent(TPU_PARTIALS, intent_path=intent_path, manifest=manifest)

    # Intent file holds the uploaded partials verbatim.
    assert source.has_intent(intent)
    assert json.loads(intent_path.read_text()) == TPU_PARTIALS
    # Manifest sibling holds the v1 schema.
    mpath = manifest_path_for(intent_path)
    assert mpath.exists()
    body = json.loads(mpath.read_text())
    assert body["manifest_version"] == MANIFEST_VERSION == "1"
    assert body["portal_label"] == "Rosa Flex 96A"
    assert body["imported_by"] == str(imported_by)
    assert body["status"] == "published"
    assert body["compatibility"] == {"compatible": True, "reason": None}
    assert body["provenance"]["orca_version"] == ORCA_VERSION
    # No temp leftovers.
    assert not list(intent_path.parent.glob(".*tmp*"))


def test_publish_upserts_in_place(tmp_path: Path) -> None:
    _seed_system_tree(tmp_path)
    source = VendoredProfileSource(tmp_path)
    intent = _intent("PLA", "standard")
    intent_path = source.intent_path(intent)

    m1 = build_manifest(
        portal_label="first",
        imported_by=uuid.uuid4(),
        imported_at="2026-06-05T00:00:00+00:00",
        original_filename="a.json",
        compatible=True,
        compat_reason=None,
        source_system_tree_hash="h",
        orca_version=ORCA_VERSION,
    )
    publish_intent(PLA_PARTIALS, intent_path=intent_path, manifest=m1)
    assert read_manifest_label(intent_path) == "first"

    m2 = {**m1, "portal_label": "second"}
    publish_intent(PLA_PARTIALS, intent_path=intent_path, manifest=m2)
    assert read_manifest_label(intent_path) == "second"  # overwrote in place


def test_read_manifest_label_missing_is_none(tmp_path: Path) -> None:
    _seed_system_tree(tmp_path)
    source = VendoredProfileSource(tmp_path)
    # No manifest written yet for this slot → None.
    assert read_manifest_label(source.intent_path(_intent("PETG", "strong"))) is None


def test_staged_source_inherits_real_tree_but_serves_uploaded_partials(tmp_path: Path) -> None:
    _seed_system_tree(tmp_path)
    intent = _intent("TPU", "standard")
    staged = StagedProfileSource(tmp_path, staged_partials=TPU_PARTIALS, staged_intent=intent)
    # Inherits the real system tree.
    assert "Rosa3D Flex 96A" in staged.system_tree()
    # Serves the uploaded partials + reports the staged intent present, WITHOUT a disk file.
    assert staged.has_intent(intent) is True
    assert staged.intent_partials(intent) == TPU_PARTIALS
    assert not VendoredProfileSource(tmp_path).has_intent(intent)


def test_validate_import_does_not_touch_a_real_bundle_store(tmp_path: Path) -> None:
    # Belt-and-braces: even with a real BundleStore present on disk, the validation path
    # writes nothing into it (the no-persist store is used internally).
    _seed_system_tree(tmp_path)
    store_root = tmp_path / "bundle-store"
    store = BundleStore(store_root)
    before = list(store_root.rglob("*")) if store_root.exists() else []
    validate_import(
        PLA_PARTIALS, _intent("PLA", "standard"), real_root=tmp_path, orca_version=ORCA_VERSION
    )
    after = list(store_root.rglob("*")) if store_root.exists() else []
    assert before == after == []
    assert store.load_bundle("deadbeef") is None


# === printer_ref path-traversal guards (fallback-review Critical) ============


def test_is_safe_printer_ref_accepts_the_supported_printer() -> None:
    assert is_safe_printer_ref(PRINTER_REF) is True
    assert is_safe_printer_ref("printer1") is True


@pytest.mark.parametrize(
    "bad",
    [
        "../../tmp/evil",
        "..",
        "../etc",
        "/etc/passwd",
        "a/b",
        "a\\b",
        ".hidden",
        "",
        "UPPER",  # charset is intentionally lowercase-only (matches the one supported ref)
        "with space",
        "a/../../b",
    ],
)
def test_is_safe_printer_ref_rejects_traversal_and_separators(bad: str) -> None:
    assert is_safe_printer_ref(bad) is False


def test_is_within_intents_root_contains_legitimate_slot(tmp_path: Path) -> None:
    _seed_system_tree(tmp_path)
    intent_path = VendoredProfileSource(tmp_path).intent_path(_intent("PLA", "standard"))
    assert is_within_intents_root(tmp_path, intent_path) is True


def test_is_within_intents_root_rejects_escaping_target(tmp_path: Path) -> None:
    # A path that climbs out of <root>/intents must be rejected even if it were constructed.
    escaping = tmp_path / "intents" / ".." / ".." / "tmp" / "evil" / "x.json"
    assert is_within_intents_root(tmp_path, escaping) is False


# === rollback-safe intent+manifest publish (fallback-review High) ============


def _fail_rename_on_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ONLY the manifest commit to fail, leaving the intent commit to succeed."""
    real_rename = os.rename

    def fake_rename(src, dst, *args, **kwargs):
        if str(dst).endswith(".manifest.json"):
            raise OSError("simulated manifest write failure")
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr(import_service.os, "rename", fake_rename)


def test_publish_manifest_failure_on_fresh_import_leaves_no_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_system_tree(tmp_path)
    source = VendoredProfileSource(tmp_path)
    intent = _intent("PETG", "standard")
    intent_path = source.intent_path(intent)
    manifest = build_manifest(
        portal_label="x",
        imported_by=uuid.uuid4(),
        imported_at="2026-06-05T00:00:00+00:00",
        original_filename="a.json",
        compatible=True,
        compat_reason=None,
        source_system_tree_hash="h",
        orca_version=ORCA_VERSION,
    )
    before = _snapshot(tmp_path)

    _fail_rename_on_manifest(monkeypatch)
    with pytest.raises(OSError, match="simulated manifest write failure"):
        publish_intent(PLA_PARTIALS, intent_path=intent_path, manifest=manifest)

    # Fresh import rolled back: NO intent, NO manifest, NO temp leftovers; tree byte-identical.
    assert not intent_path.exists()
    assert not manifest_path_for(intent_path).exists()
    assert not list(intent_path.parent.glob(".*tmp*"))
    assert _snapshot(tmp_path) == before


def test_publish_manifest_failure_on_reimport_restores_previous_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_system_tree(tmp_path)
    source = VendoredProfileSource(tmp_path)
    intent = _intent("PLA", "standard")
    intent_path = source.intent_path(intent)

    first = build_manifest(
        portal_label="first",
        imported_by=uuid.uuid4(),
        imported_at="2026-06-05T00:00:00+00:00",
        original_filename="first.json",
        compatible=True,
        compat_reason=None,
        source_system_tree_hash="h",
        orca_version=ORCA_VERSION,
    )
    publish_intent(PLA_PARTIALS, intent_path=intent_path, manifest=first)
    before = _snapshot(tmp_path)

    # Now a re-import whose manifest commit fails must restore the PRIOR intent+manifest pair.
    second = {**first, "portal_label": "second"}
    _fail_rename_on_manifest(monkeypatch)
    with pytest.raises(OSError, match="simulated manifest write failure"):
        publish_intent(TPU_PARTIALS, intent_path=intent_path, manifest=second)

    assert _snapshot(tmp_path) == before  # byte-identical to the prior successful import
    assert json.loads(intent_path.read_text()) == PLA_PARTIALS  # NOT the failed TPU re-import
    assert read_manifest_label(intent_path) == "first"  # NOT "second"
    assert not list(intent_path.parent.glob(".*tmp*"))


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_publish_intent_preserves_existing_intent_mode_and_manifest_inherits_it(tmp_path):
    """Runtime smoke regression: mkstemp must not publish root-owned/0600 vendored files."""
    root = tmp_path / "vendored"
    intent_path = root / "intents" / "creality-k1-max-microswiss-hf" / "TPU" / "standard.json"
    intent_path.parent.mkdir(parents=True)
    intent_path.write_text('{"machine":{},"process":{},"filament":{}}', encoding="utf-8")
    intent_path.chmod(0o664)

    from app.modules.slicer.import_service import manifest_path_for, publish_intent

    publish_intent(
        {"machine": {}, "process": {}, "filament": {}},
        intent_path=intent_path,
        manifest={"manifest_version": "1", "portal_label": "Rosa Flex"},
    )

    manifest_path = manifest_path_for(intent_path)
    assert oct(intent_path.stat().st_mode & 0o777) == "0o664"
    assert oct(manifest_path.stat().st_mode & 0o777) == "0o664"
