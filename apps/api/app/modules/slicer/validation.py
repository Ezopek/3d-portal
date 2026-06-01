"""CLI-acceptance validator seam + the specified Orca smoke command (Story 32.1).

The resolver calls a :class:`CliValidator` in its validate step (Decision AH § 5)
*before* a triple becomes a bundle. This story ships:

- the interface (:class:`CliValidator`) + a :class:`NullCliValidator` (always-OK)
  used by the pure unit suite — the merge/hash/precedence tests need no real Orca;
- the exact specified Orca smoke command (constant + :func:`build_orca_smoke_command`)
  that the real validator (Story 32.2, inside the slicer-worker container) will run;
- a required-key schema assertion (:func:`check_required_keys`).

**Actual Orca execution is NOT implemented here** — the container is Story 32.2
(OD-2). A real-Orca acceptance smoke test exists in the suite but is env-gated
(``ORCA_SMOKE_TEST=1``), default-skipped in CI and autonomous runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.modules.slicer.models import MaterialClass, ResolvedTriple

# The exact smoke command spec the real (Story 32.2) validator runs: an Orca
# ``--info`` pass over the three resolved JSONs that must exit 0 for the triple to
# be accepted. ``orca`` is the AppImage-extracted entrypoint inside the
# slicer-worker container (Decision AI). Documented as a constant so the spec is
# pinned now even though execution lands in Story 32.2.
ORCA_SMOKE_COMMAND_TEMPLATE = (
    'orca --info --load-settings "<machine.json>;<process.json>" '
    '--load-filaments "<filament.json>" <probe.stl>'
)

# Material classes whose resolved filament MUST carry a sane
# ``filament_max_volumetric_speed`` (e.g. TPU prints fail/blob without it). A
# missing/zero value is a classified ``invalid_partial`` failure, never a silent
# resolve to a wrong default (AC-9).
_REQUIRE_VOLUMETRIC_SPEED: frozenset[MaterialClass] = frozenset({"TPU"})

_VOLUMETRIC_SPEED_KEY = "filament_max_volumetric_speed"


class ValidationResult(BaseModel):
    """Outcome of a validator/schema check: OK, or not-OK with a reason."""

    ok: bool
    reason: str | None = None


@runtime_checkable
class CliValidator(Protocol):
    """The CLI-acceptance seam the resolver calls before persisting a bundle."""

    def validate(self, triple: ResolvedTriple) -> ValidationResult:
        """Return whether ``triple`` is CLI-acceptable (a dry ``--info`` smoke)."""
        ...


class NullCliValidator:
    """Always-OK validator for the pure unit suite (no real Orca binary)."""

    def validate(self, triple: ResolvedTriple) -> ValidationResult:
        return ValidationResult(ok=True)


def build_orca_smoke_command(
    machine: Path, process: Path, filament: Path, probe_stl: Path
) -> list[str]:
    """Build the concrete Orca ``--info`` smoke argv (used by the bench-gated test).

    Mirrors :data:`ORCA_SMOKE_COMMAND_TEMPLATE`. This story does not execute it in
    CI; Story 32.2 wires the real container run.
    """
    return [
        "orca",
        "--info",
        "--load-settings",
        f"{machine};{process}",
        "--load-filaments",
        str(filament),
        str(probe_stl),
    ]


def _first_value(raw: object) -> object:
    """Orca stores scalars as single-element arrays; unwrap defensively."""
    if isinstance(raw, list):
        return raw[0] if raw else None
    return raw


def check_required_keys(triple: ResolvedTriple, material_class: MaterialClass) -> ValidationResult:
    """Assert material-class-required keys are present and sane (AC-9).

    Currently: TPU (and any class in ``_REQUIRE_VOLUMETRIC_SPEED``) MUST carry a
    positive ``filament_max_volumetric_speed``. Failure ⇒ classified
    ``invalid_partial`` at the resolver.
    """
    if material_class in _REQUIRE_VOLUMETRIC_SPEED:
        value = _first_value(triple.filament.get(_VOLUMETRIC_SPEED_KEY))
        if value is None:
            return ValidationResult(
                ok=False,
                reason=(f"{material_class} filament missing required {_VOLUMETRIC_SPEED_KEY!r}"),
            )
        try:
            if float(value) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return ValidationResult(
                ok=False,
                reason=(
                    f"{material_class} {_VOLUMETRIC_SPEED_KEY!r} not a positive number: {value!r}"
                ),
            )
    return ValidationResult(ok=True)
