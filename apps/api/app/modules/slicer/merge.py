"""Pure recursive Orca inheritance merge + CLI normalization (Story 32.1).

No I/O, no clocks, no randomness, no global state — every function here is a pure
transform over plain dicts, so it is unit-testable against the checked-in
fixtures and contributes nothing non-deterministic to ``bundle_hash``.

Why a first-class merge (Decision AH): raw Orca **user** profiles are *partial* —
they ``inherit`` a system profile (which may itself inherit a parent) and lack a
top-level ``type``, so the Orca CLI rejects them directly. The merge IS the
load-bearing complexity that the naive ``--load-settings`` path fails on.

[Source: architecture.md § Decision AH §§ 2-3; productionizes the bench PoC]
"""

from __future__ import annotations

from typing import Any

from app.modules.slicer.models import ProfileKind

# The Orca key naming the parent a profile derives from. Resolved away in the
# merged output (it is a recipe input, not a slicing setting).
_INHERIT_KEY = "inherit"

# The Orca key that resolved-system profiles carry and that the CLI ``--load-*``
# path rejects; dropped during normalization (proven by the bench PoC — AC-4).
_INSTANTIATION_KEY = "instantiation"


class MissingSystemProfileError(Exception):
    """An ``inherit`` chain references a system profile not in the vendored tree.

    Surfaced by the resolver as the classified ``missing_system_profile`` failure
    (AC-7) — never a silent partial merge.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"inherited system profile not found: {name!r}")


class InvalidPartialError(Exception):
    """A partial is structurally malformed in a way the merge cannot resolve.

    Currently raised when an ``inherit`` value is not a system-profile *name*
    string (e.g. a list or number): such a value cannot key into the system tree
    and would otherwise leak a bare ``TypeError``/``KeyError`` out of the merge.
    Surfaced by the resolver as the classified ``invalid_partial`` failure (AC-7).
    """


def _deep_merge(parent: dict, child: dict) -> dict:
    """Return ``parent`` deep-merged with ``child``; child wins on every conflict.

    Nested dicts merge recursively; scalars/lists are replaced wholesale by the
    child (the most-derived layer). Neither input is mutated.
    """
    merged: dict[str, Any] = dict(parent)
    for key, child_value in child.items():
        parent_value = merged.get(key)
        if isinstance(parent_value, dict) and isinstance(child_value, dict):
            merged[key] = _deep_merge(parent_value, child_value)
        else:
            merged[key] = child_value
    return merged


def resolve_inheritance(system_tree: dict[str, dict], user_partial: dict) -> dict:
    """Recursively resolve the Orca ``inherit`` chain; the user partial wins (AC-3).

    ``system_tree`` maps a system profile ``name`` → its raw JSON dict. The
    ``user_partial`` ``inherit``s a system profile, which may itself ``inherit`` a
    parent (a ≥2-level chain). Profiles are merged from the most-base ancestor up
    to the user partial, deep-merging child-over-parent, so the user partial is the
    most-derived layer and wins on every conflict. The ``inherit`` key is resolved
    away from the result.

    Raises :class:`MissingSystemProfileError` if any ``inherit`` reference is
    absent from ``system_tree`` (no silent partial merge).
    """
    # Walk the chain from the user partial down to the base ancestor, collecting
    # each layer most-derived-first; guard against inherit cycles.
    chain: list[dict] = [user_partial]
    seen: set[str] = set()
    current = user_partial
    while _INHERIT_KEY in current:
        parent_name = current[_INHERIT_KEY]
        # ``inherit`` must name a single system profile; anything else (list, dict,
        # number, …) is a malformed partial, not a missing/cyclic reference. Reject
        # it here so it classifies as ``invalid_partial`` rather than leaking a bare
        # ``TypeError: unhashable type`` from the cycle/lookup checks below.
        if not isinstance(parent_name, str):
            raise InvalidPartialError(
                f"{_INHERIT_KEY!r} must be a system-profile name string, "
                f"got {type(parent_name).__name__}: {parent_name!r}"
            )
        if parent_name in seen:
            raise MissingSystemProfileError(f"{parent_name} (inherit cycle)")
        seen.add(parent_name)
        parent = system_tree.get(parent_name)
        if parent is None:
            raise MissingSystemProfileError(parent_name)
        chain.append(parent)
        current = parent

    # Merge base → … → user partial (reverse of the most-derived-first chain).
    merged: dict[str, Any] = {}
    for layer in reversed(chain):
        merged = _deep_merge(merged, layer)
    merged.pop(_INHERIT_KEY, None)
    return merged


def normalize_for_cli(merged: dict, *, profile_kind: ProfileKind) -> dict:
    """Make a merged profile CLI-acceptable (AC-4). Returns a new dict; no mutation.

    - Injects the top-level ``type`` (``machine``/``process``/``filament``) that
      raw user partials lack — the exact omission that makes the Orca CLI reject
      raw partials (``--datadir`` does not fix it; proven by the bench PoC).
    - Drops the ``instantiation`` field that the CLI ``--load-*`` path rejects.
    - Leaves every slicing-relevant key intact (no lossy normalization) — in
      particular the full process JSON survives for AC-11 forward-compat.
    """
    normalized = dict(merged)
    normalized.pop(_INSTANTIATION_KEY, None)
    normalized.pop(_INHERIT_KEY, None)  # defensive — resolve_inheritance already drops it
    normalized["type"] = profile_kind
    return normalized
