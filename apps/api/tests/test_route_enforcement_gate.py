"""Initiative 6 Story 11.4 Decision M — route enforcement gate.

Iterates the live FastAPI route table (`app.routes`) and asserts every
`/api/*` route either has an authentication Depends OR appears in the
`_PUBLIC_ROUTES` allowlist. Drift between architecture intent and shipped
code (the proximate root cause of supplemental finding High-002 — Init 5
Story 9.2 audit miss + Story 10.3 cutover exposure) becomes a CI failure
instead of a production privacy regression.

The check is mechanical:
  1. Filter `app.routes` to `APIRoute` instances with path starting `/api/`.
  2. For each route, inspect `route.dependant.dependencies` for any Depends
     whose `call` resolves to one of the known auth dependency callables.
  3. If no auth Depends present, assert the route path matches an entry in
     `apps/api/app/main.py:_PUBLIC_ROUTES`.

NFR6-PERF-1: <1 second runtime; no DB I/O; pure route-table introspection.

The known auth-dependency callable names (currently 4 in the codebase):
  - `_current_user_dep` → `current_user` (any authenticated role)
  - `_current_admin_dep` → `current_admin` (admin only)
  - `_current_member_or_admin_dep` → `current_member_or_admin` (member+admin)
  - `_current_admin_or_agent_dep` → `current_admin_or_agent` (admin+agent)

Adding a new auth-dependency variant requires extending `_AUTH_DEP_NAMES`
below; the test will flag any new route that uses an unrecognized auth
function (defense against silent expansion of the trust surface).
"""

from fastapi.routing import APIRoute

from app.main import _PUBLIC_ROUTES, create_app

# Set of dependency function names that the route enforcement gate recognizes
# as "authentication". Extending this set is a meaningful policy decision and
# requires explicit code review (the test fails closed on unrecognized names).
_AUTH_DEP_NAMES: frozenset[str] = frozenset(
    {
        "_current_user_dep",
        "_current_admin_dep",
        "_current_member_or_admin_dep",
        "_current_admin_or_agent_dep",
    }
)


def _route_has_auth_depends(route: APIRoute) -> bool:
    """Return True if any of the route's top-level Depends resolves to an
    auth dependency callable in `_AUTH_DEP_NAMES`."""
    for dep in route.dependant.dependencies:
        if dep.call is not None and getattr(dep.call, "__name__", "") in _AUTH_DEP_NAMES:
            return True
    return False


def test_every_api_route_has_auth_depends_or_is_in_public_allowlist():
    """Story 11.4 / Decision M canonical check.

    Every route mounted under `/api/*` (any HTTP method) must either:
      (a) have an explicit auth `Depends(current_*)` parameter, OR
      (b) appear literally in `_PUBLIC_ROUTES`.

    A failing assertion means one of two scenarios:
      1. A new route was added without an auth Depends and not in the
         allowlist → potential privacy regression (the bug class that
         produced supplemental finding High-002).
      2. A new auth-dependency variant was introduced but not added to
         `_AUTH_DEP_NAMES` above → test cannot recognize the new auth
         function and treats the route as anonymous.

    Fix path: add the auth Depends to the route OR add the path to
    `_PUBLIC_ROUTES` (requires SCP per FR6-AUTH-2) OR extend
    `_AUTH_DEP_NAMES` after explicit code review.
    """
    app = create_app()
    public_allowlist = frozenset(_PUBLIC_ROUTES)

    violations: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/"):
            continue
        if _route_has_auth_depends(route):
            continue
        if route.path in public_allowlist:
            continue
        methods = sorted(route.methods - {"HEAD"})
        violations.append(f"{route.path} (methods={methods})")

    assert not violations, (
        "Initiative 6 Story 11.4 / Decision M — the following /api/* routes have "
        "neither an auth Depends NOR an entry in apps/api/app/main.py:_PUBLIC_ROUTES. "
        "Fix by adding `Depends(current_*)` to the handler OR adding the path "
        "to _PUBLIC_ROUTES via a Sprint Change Proposal (FR6-AUTH-2). "
        f"Violations: {violations}"
    )


def test_public_routes_allowlist_matches_actual_route_table():
    """Defense against stale `_PUBLIC_ROUTES` entries: every entry in the
    allowlist must correspond to a real registered route. Otherwise the
    allowlist accumulates dead entries that mask future drift (e.g. a
    deleted route's allowlist entry could later collide with a new route
    of the same path).
    """
    app = create_app()
    registered_paths = {
        r.path for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api/")
    }

    stale_entries = [p for p in _PUBLIC_ROUTES if p not in registered_paths]
    assert not stale_entries, (
        "Initiative 6 Story 11.4 — `_PUBLIC_ROUTES` contains entries that do not match "
        "any currently-registered route. Stale entries mask future drift; remove them. "
        f"Stale: {stale_entries}"
    )


def test_no_unrecognized_auth_dep_in_route_table():
    """Defense against silent auth-dependency expansion: every `_current_*`
    callable used as a route Depends must be in `_AUTH_DEP_NAMES`. A new
    auth dependency function landing without an update to this test is
    a meaningful policy decision that needs explicit review.
    """
    app = create_app()
    unknown_auth_deps: set[str] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/"):
            continue
        for dep in route.dependant.dependencies:
            if dep.call is None:
                continue
            name = getattr(dep.call, "__name__", "")
            if name.startswith("_current_") and name not in _AUTH_DEP_NAMES:
                unknown_auth_deps.add(name)

    assert not unknown_auth_deps, (
        "Initiative 6 Story 11.4 — discovered unrecognized `_current_*` auth "
        "dependency callables in the route table. Add them to `_AUTH_DEP_NAMES` "
        "after explicit code review confirming the new trust tier is intentional. "
        f"Unrecognized: {sorted(unknown_auth_deps)}"
    )
