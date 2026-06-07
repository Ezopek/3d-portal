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

# The Orca keys naming the parent a profile derives from. Resolved away in the
# merged output (a recipe input, not a slicing setting). Real Orca USER profiles
# carry the PLURAL ``inherits``; the bench/legacy exports carry singular
# ``inherit``. Both are resolved equivalently — a published offer chain built from
# real Orca blocks must merge its system parent, not leak an unresolved key into
# the headless-CLI bundle (PROFILE-PUBLISH-FIX; mirrors ``profile_library.declared_inherit``).
# Plural is checked first so a profile carrying both keys prefers the real-Orca one.
_INHERIT_KEYS = ("inherits", "inherit")

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


def _inherit_ref(body: dict) -> tuple[str | None, object]:
    """Return ``(key, raw_value)`` for whichever inherit key is present, else ``(None, None)``.

    Preference order is :data:`_INHERIT_KEYS` (plural ``inherits`` first), so a profile
    carrying both keys resolves against the real-Orca one. The raw value is returned
    unvalidated so the caller can classify a non-string parent as ``invalid_partial``
    rather than silently treating it as "no parent".
    """
    for key in _INHERIT_KEYS:
        if key in body:
            return key, body[key]
    return None, None


def _drop_inherit_keys(body: dict) -> None:
    """Strip every inherit recipe key (plural and singular) from ``body`` in place."""
    for key in _INHERIT_KEYS:
        body.pop(key, None)


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
    """Recursively resolve the Orca inherit chain; the user partial wins (AC-3).

    ``system_tree`` maps a system profile ``name`` → its raw JSON dict. The
    ``user_partial`` inherits a system profile (via plural ``inherits`` for real Orca
    user exports, or singular ``inherit`` for the bench/legacy shape — both handled
    equivalently), which may itself inherit a parent (a ≥2-level chain). Profiles are
    merged from the most-base ancestor up to the user partial, deep-merging
    child-over-parent, so the user partial is the most-derived layer and wins on every
    conflict. Every inherit recipe key is resolved away from the result.

    Raises :class:`MissingSystemProfileError` if any inherit reference is absent from
    ``system_tree`` (no silent partial merge — the failure that previously hid behind
    a plural ``inherits`` leak and surfaced only as Orca RC -17).
    """
    # Walk the chain from the user partial down to the base ancestor, collecting
    # each layer most-derived-first; guard against inherit cycles.
    chain: list[dict] = [user_partial]
    seen: set[str] = set()
    current = user_partial
    while True:
        key, parent_name = _inherit_ref(current)
        if key is None:
            break
        # An inherit key must name a single system profile; anything else (list, dict,
        # number, …) is a malformed partial, not a missing/cyclic reference. Reject
        # it here so it classifies as ``invalid_partial`` rather than leaking a bare
        # ``TypeError: unhashable type`` from the cycle/lookup checks below.
        if not isinstance(parent_name, str):
            raise InvalidPartialError(
                f"{key!r} must be a system-profile name string, "
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
    _drop_inherit_keys(merged)
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
    # Defensive — resolve_inheritance already drops every inherit key; strip both the
    # plural ``inherits`` and singular ``inherit`` so neither can ever reach the
    # headless-CLI bundle even on a normalize-only path (PROFILE-PUBLISH-FIX).
    _drop_inherit_keys(normalized)
    normalized["type"] = profile_kind
    return normalized
