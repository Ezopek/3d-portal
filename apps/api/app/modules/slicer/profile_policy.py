"""Portal-owned profile-selection policy (Story 35.1, Init 23 / Epic E35, Decision AS).

Spoolman stays the source of truth for filament inventory + the generic material type;
the PORTAL owns the mapping from that material — and optionally from a specific Spoolman
filament — to a concrete Orca ``FilamentProfile``. This module is the pure, standalone
foundation of that policy:

- :class:`EstimateProfileSource` — the classified provenance of an estimate's filament
  profile (exact override / material default / unavailable);
- :func:`normalize_material` — the portal-boundary normalization (trim + uppercase);
- the policy models (:class:`MaterialDefault`, :class:`FilamentOverride`,
  :class:`ProfilePolicy`) + the pure precedence resolver
  :meth:`ProfilePolicy.resolve_selection`;
- :class:`ProfilePolicyStore` — a filesystem-backed JSON store with atomic publish +
  flock + mtime-cached load (mirrors ``attribution_store`` / ``estimate_store``);
- :func:`unknown_profile_refs` — a pure validation seam for the admin save path.

Resolution precedence is the load-bearing contract: **exact filament override >
material-type default > unavailable**. A disabled entry falls through to the next level.
Overrides are keyed by the churn-stable ``spoolman_filament_ref()`` (vendor∥material∥name),
NEVER the integer Spoolman id (NFR23-STABLE-KEY-1).

No resolver/API/worker coupling lives here — that is Story 35.2+. This slice is
deploy-clean (no Alembic, no worker image change).

[Source: epics.md § Initiative 23 / Story 35.1; SCP 2026-06-07 § Task 1 + § Data model target]
"""

from __future__ import annotations

import fcntl
import os
import tempfile
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from collections.abc import Iterator

# The single store filename under the policy dir. Identity (vendor∥material∥name) ref
# keys + normalized material keys are the JSON content; this is the only path literal.
_POLICY_FILENAME = "profile_policy.json"


class EstimateProfileSource(StrEnum):
    """Classified provenance of the Orca filament profile chosen for an estimate (AC-1).

    Returned to the estimate read APIs/UI (Story 35.3+) so a fallback estimate is never
    presented as exact and a missing profile is an explicit, non-blocking absence.
    """

    exact_filament_mapping = "exact_filament_mapping"
    default_material_profile = "default_material_profile"
    unavailable_no_profile = "unavailable_no_profile"


def normalize_material(raw: str | None) -> str | None:
    """Normalize a Spoolman material string at the portal boundary (AC-2).

    Trim + uppercase; an empty/blank/``None`` input becomes ``None`` (unconfigured —
    surfaced as such by the admin UI), NOT an invented or coerced category. This is a
    pure case/whitespace fold ONLY: ``"PLA+"`` stays ``"PLA+"`` — there is deliberately
    no alias table folding ``PLA+``→``PLA`` (the SCP "material spelling drift" guardrail;
    add an explicit alias table later if ever wanted, never a silent coercion).
    """
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    return trimmed.upper()


class MaterialDefault(BaseModel):
    """Default Orca filament profile for a generic material type (AC-3)."""

    model_config = ConfigDict(extra="forbid")

    orca_filament_profile_ref: str
    enabled: bool = True


class FilamentOverride(BaseModel):
    """Exact Orca filament profile pinned to one Spoolman filament ref (AC-3)."""

    model_config = ConfigDict(extra="forbid")

    orca_filament_profile_ref: str
    enabled: bool = True


class ProfileSelection(BaseModel):
    """Result of resolving the profile policy for a (material, filament) selection (AC-9).

    ``orca_filament_profile_ref`` is ``None`` iff ``source`` is ``unavailable_no_profile``.
    ``selected_material`` is the NORMALIZED material (or ``None`` when unconfigured/unknown).
    ``selected_spoolman_filament_ref`` is carried ONLY for an exact mapping, so a caller can
    tell a per-filament estimate apart from a shared material-default one.
    """

    model_config = ConfigDict(frozen=True)

    source: EstimateProfileSource
    orca_filament_profile_ref: str | None = None
    selected_material: str | None = None
    selected_spoolman_filament_ref: str | None = None


class ProfilePolicy(BaseModel):
    """Portal-owned profile-selection policy (AC-4).

    ``material_defaults`` is keyed by NORMALIZED material (trim + uppercase, applied at
    construction so ``" pla "`` and ``"PLA"`` collapse to one entry). ``filament_overrides``
    is keyed by the churn-stable ``spoolman_filament_ref()`` (vendor∥material∥name), NEVER
    the integer Spoolman id (AC-12 / NFR23-STABLE-KEY-1).
    """

    model_config = ConfigDict(extra="forbid")

    material_defaults: dict[str, MaterialDefault] = {}
    filament_overrides: dict[str, FilamentOverride] = {}

    @field_validator("material_defaults", mode="before")
    @classmethod
    def _normalize_default_keys(cls, value: object) -> object:
        # Normalize material-default keys at the boundary so a config that writes " pla "
        # and a resolve that looks up "PLA" cannot diverge. A blank key normalizes to None
        # and is dropped (an unconfigured material is simply absent). Non-dict input is left
        # for pydantic to reject with its own error.
        if not isinstance(value, dict):
            return value
        normalized: dict[str, object] = {}
        for key, entry in value.items():
            norm = normalize_material(key) if isinstance(key, str) else key
            if norm is None:
                continue
            normalized[norm] = entry
        return normalized

    def resolve_selection(
        self,
        *,
        material: str | None,
        spoolman_filament_ref: str | None = None,
    ) -> ProfileSelection:
        """Resolve the Orca filament profile by policy precedence (AC-5..AC-9).

        Precedence (load-bearing contract):

        1. **exact override** — ``spoolman_filament_ref`` present + an ``enabled`` entry in
           ``filament_overrides`` ⇒ ``exact_filament_mapping``;
        2. **material default** — a normalized ``material`` present + an ``enabled`` entry in
           ``material_defaults`` ⇒ ``default_material_profile``;
        3. **unavailable** — otherwise ``unavailable_no_profile`` (profile ref ``None``).

        A DISABLED entry falls through to the next level (a disabled override → material
        default → unavailable; a disabled default → unavailable). Pure + deterministic:
        same inputs ⇒ same :class:`ProfileSelection`, no clock, no external read.
        """
        normalized_material = normalize_material(material)

        if spoolman_filament_ref is not None:
            override = self.filament_overrides.get(spoolman_filament_ref)
            if override is not None and override.enabled:
                return ProfileSelection(
                    source=EstimateProfileSource.exact_filament_mapping,
                    orca_filament_profile_ref=override.orca_filament_profile_ref,
                    selected_material=normalized_material,
                    selected_spoolman_filament_ref=spoolman_filament_ref,
                )

        if normalized_material is not None:
            default = self.material_defaults.get(normalized_material)
            if default is not None and default.enabled:
                return ProfileSelection(
                    source=EstimateProfileSource.default_material_profile,
                    orca_filament_profile_ref=default.orca_filament_profile_ref,
                    selected_material=normalized_material,
                )

        return ProfileSelection(
            source=EstimateProfileSource.unavailable_no_profile,
            orca_filament_profile_ref=None,
            selected_material=normalized_material,
        )


def unknown_profile_refs(policy: ProfilePolicy, known_refs: set[str]) -> set[str]:
    """Return policy Orca profile refs absent from ``known_refs`` (AC-13).

    A pure validation seam for the admin save path (Story 35.4): the caller supplies the
    set of available/vendored Orca filament profile refs and this reports which configured
    refs would not resolve — so a save can be rejected before a deferred RC -17-style
    failure. NO concrete Orca ref is hard-coded here; the known set is the caller's input.
    """
    configured = {d.orca_filament_profile_ref for d in policy.material_defaults.values()}
    configured |= {o.orca_filament_profile_ref for o in policy.filament_overrides.values()}
    return configured - known_refs


class ProfilePolicyStore:
    """Filesystem-backed JSON policy store with atomic publish + mtime-cached load.

    Reads/writes a single ``profile_policy.json`` under ``root``. The atomic-publish +
    flock idiom mirrors ``attribution_store`` / ``estimate_store`` (temp + fsync +
    ``os.replace`` so a concurrent reader never sees a partial file). :meth:`load` caches
    the parsed policy keyed on the file's mtime+size, re-reading only when the file
    changes — so the policy can be read on demand without a restart (AC-11).
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._cache: tuple[tuple[int, int], ProfilePolicy] | None = None

    @property
    def path(self) -> Path:
        return self._root / _POLICY_FILENAME

    def load(self) -> ProfilePolicy:
        """Return the persisted policy, or an empty one when the file is absent (AC-10).

        mtime+size keyed cache (AC-11): an unchanged file returns the cached parse; a save
        (which bumps mtime / size) invalidates it on the next load.
        """
        path = self.path
        try:
            stat = path.stat()
        except FileNotFoundError:
            self._cache = None
            return ProfilePolicy()
        cache_key = (stat.st_mtime_ns, stat.st_size)
        if self._cache is not None and self._cache[0] == cache_key:
            return self._cache[1]
        policy = ProfilePolicy.model_validate_json(path.read_text(encoding="utf-8"))
        self._cache = (cache_key, policy)
        return policy

    def save(self, policy: ProfilePolicy) -> None:
        """Atomically (re)publish the policy JSON under an exclusive lock (AC-11)."""
        path = self.path
        with self._record_lock(path):
            self._atomic_publish(path, policy.model_dump_json(indent=2))
        # Drop the cache so the next load re-stats and re-parses the just-written file.
        self._cache = None

    # --- internals (mirror attribution_store's lock + atomic publish) ---------------

    @staticmethod
    @contextmanager
    def _record_lock(path: Path) -> Iterator[None]:
        """Exclusive advisory lock over the publish, on a sibling ``.<name>.lock`` sidecar.

        ``flock`` is per-open-file-description, serializing writers across processes (the
        shared ``portal-content`` volume) and threads alike. The lock is never on the record
        file itself so the atomic ``os.replace`` publish is untouched.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.parent / f".{path.name}.lock"
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @staticmethod
    def _atomic_publish(path: Path, content: str) -> Path:
        """Atomically (re)publish ``content`` to ``path`` (create or overwrite).

        Content is fully written + fsynced to a UNIQUE temp file in the target dir, then
        ``os.replace`` swaps it in atomically (POSIX rename) — a concurrent reader never
        sees a partial file. On any failure the temp file is removed.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        return path


def load_profile_policy() -> ProfilePolicy:
    """Settings-wired convenience: load the policy from the configured store dir (AC-14).

    Reads ``slicer_profile_policy_dir`` from settings — NEVER a hard-coded path — mirroring
    ``resolve_intent``'s settings-wiring. A fresh store is constructed per call (the mtime
    cache lives on the store instance); callers that read hot should hold a store instance.
    """
    from app.core.config import get_settings

    return ProfilePolicyStore(get_settings().slicer_profile_policy_dir).load()
