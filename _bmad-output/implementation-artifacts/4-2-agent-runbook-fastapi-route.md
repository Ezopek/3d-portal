# Story 4.2: `/agent-runbook` FastAPI Route + Deploy Verify

Status: done

## Story

As a fresh-session AI agent invoked with no prior repo knowledge,
I want `GET https://3d.ezop.ddns.net/agent-runbook` to return the canonical runbook content as `text/markdown`,
So that one URL bootstrap suffices to learn the portal's operational surface, without needing repo access.

## Acceptance Criteria

**Given** `docs/agents-add-model-runbook.md` exists (Story 4.1) and `infra/.runbook-fingerprint` contains the sha256 line `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` (Story 4.1 baseline),

**When** Story 4.2 ships:

1. **New FastAPI module** `apps/api/app/modules/runbook/__init__.py` + `apps/api/app/modules/runbook/router.py` exposing `GET /agent-runbook` as `PlainTextResponse` reading from `/app/static/agent-runbook.md`. Module structure mirrors existing modules (`apps/api/app/modules/admin/router.py`, `apps/api/app/modules/sot/router.py`). Decision A from `architecture.md` § Initiative 2.
2. **Router mounted** in `apps/api/app/router.py` with NO auth dependencies — public read per Decision B. The `/agent-runbook` path is intentionally NOT under `/api/` (it is conceptually a top-level discovery resource, not an API).
3. **Dockerfile updated** — `apps/api/Dockerfile` adds `COPY docs/agents-add-model-runbook.md /app/static/agent-runbook.md` in the build stage. Static file lives at deterministic image path. Build context already includes the repo root, so `docs/agents-add-model-runbook.md` resolves.
4. **nginx config updated** — `infra/nginx-180/3d-portal.conf` adds `location /agent-runbook { proxy_pass http://api; }` (or equivalent — matching the existing `location /api/` pattern). nginx config copied to `~/repos/configs/nginx/3d-portal.conf` and deployed via that repo's `sync.sh` per project convention.
5. **Response contract** — `200 OK` with `Content-Type: text/markdown; charset=utf-8`. `503 Service Unavailable` if the file is missing from the image (deploy bug — fail loud, not silent 404). `200` with the live markdown body in the success case.
6. **Tag the route `agent-read`** is OUT OF SCOPE per Story 4.3's note (only `agent-write` exists). Add a `summary` + `description` to the route per Story 4.3's enrichment pattern (the test at `apps/api/tests/test_openapi_agent_surface.py` does NOT cover this route since `/agent-runbook` is outside `/api/`). Skipping `tags=["sot-admin"]` etc. — this is a standalone module with its own tag (`tags=["agent-runbook"]` on the router decorator) so the test filter doesn't sweep it.
7. **Deploy verify extension** — `infra/scripts/deploy.sh` (post-`alembic upgrade head`, parallel to the existing `verify-symbolication.sh` call) computes `curl https://3d.ezop.ddns.net/agent-runbook | <fingerprint-extraction-chain> | sha256sum | awk '{print $1}'` vs `$(cat infra/.runbook-fingerprint)`. The fingerprint extraction chain is the BINDING one from Story 4.1 (Completion Notes): `awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}'`. Mismatch → stderr warning (non-fatal) + `infra/.last-verify-runbook` FAILED marker. Match → `infra/.last-verify-runbook` OK marker. Same three-signal model as Initiative 1's `verify-symbolication.sh`.
8. **Smoke test on local dev:** `curl http://192.168.2.190:8090/agent-runbook` returns 200 + markdown body during `docker compose up` (LAN HTTP path — `https://` requires the .180 edge proxy reload, which depends on the `~/repos/configs/` sync).
9. **Smoke test on production after deploy:** `curl https://3d.ezop.ddns.net/agent-runbook | wc -l` returns ≥100 lines (runbook is non-empty + not truncated).
10. **Auto-deploy fires** for this commit (code + infra change) per project memory `feedback_auto_deploy_dev.md`. The nginx-edge sync to `~/repos/configs/` is a separate execution after the portal deploy lands.

**And** `ruff check apps/api` passes; `pytest apps/api/tests` full suite passes (no regressions; 424+ tests). `apps/api/tests/test_openapi_agent_surface.py` continues to pass (the new `/agent-runbook` route does NOT match the test's `TARGET_ROUTER_TAGS` filter so it doesn't need summary/description for that test).

## Tasks / Subtasks

- [x] **Task 1: Create FastAPI runbook module** (AC: 1, 5, 6)
  - [x] Create `apps/api/app/modules/runbook/__init__.py` (empty file marking the package).
  - [x] Create `apps/api/app/modules/runbook/router.py` with `APIRouter()` (no prefix — the route is `/agent-runbook` at root), `tags=["agent-runbook"]`.
  - [x] Single route `@router.get("/agent-runbook", response_class=PlainTextResponse, summary="...", description="...", responses={503: {...}})`.
  - [x] Handler reads `/app/static/agent-runbook.md` from disk, returns content. On `FileNotFoundError`, raise `HTTPException(503, "runbook missing from image — deploy bug")`.
  - [x] Set `Content-Type: text/markdown; charset=utf-8` explicitly via `Response(media_type="text/markdown; charset=utf-8")` or `PlainTextResponse(content=..., media_type="text/markdown; charset=utf-8")`.
  - [x] Use `pathlib.Path("/app/static/agent-runbook.md")` to construct the path; the read is sync (no need for async file I/O for a small markdown file).

- [x] **Task 2: Mount the router** (AC: 2)
  - [x] Edit `apps/api/app/router.py`: import `from app.modules.runbook.router import router as runbook_router` + add `api_router.include_router(runbook_router)` near the existing routers. Wait — actually, the path `/agent-runbook` is at root (no `/api/` prefix). The current `api_router` has prefix `/api`. Need to mount the runbook router on `app.main:create_app` directly with no prefix, NOT through `api_router`.
  - [x] Inspect `apps/api/app/router.py` + `apps/api/app/main.py` to locate the right include point. The runbook router goes on the FastAPI app itself, not the `/api`-prefixed sub-router.
  - [x] If `create_app()` does `app.include_router(api_router)`, add `app.include_router(runbook_router)` AFTER that line so `/agent-runbook` resolves at root.

- [x] **Task 3: Dockerfile COPY** (AC: 3)
  - [x] Inspect `apps/api/Dockerfile` (or whichever Dockerfile builds the API image — verify with `docker images` or `infra/docker-compose.yml`).
  - [x] Add `COPY docs/agents-add-model-runbook.md /app/static/agent-runbook.md` in the build stage AFTER existing COPY app statements (order matters for layer caching).
  - [x] Verify the build context in `infra/docker-compose.yml` has access to `docs/` — should be `context: ..` or repo root. If only `apps/api/` is in context, the COPY won't resolve and the build context needs adjustment.

- [x] **Task 4: nginx config** (AC: 4)
  - [x] Edit `infra/nginx-180/3d-portal.conf`: add a `location /agent-runbook { proxy_pass http://api:8000; }` block (use the upstream name + port from existing `/api/` location).
  - [x] Copy the same change into `~/repos/configs/nginx/3d-portal.conf`.
  - [x] Stage + commit the change in `~/repos/configs/` separately (it's a different repo). Run that repo's `sync.sh` to deploy.

- [x] **Task 5: deploy.sh verify extension** (AC: 7)
  - [x] Read `infra/scripts/deploy.sh` to find the verify-symbolication.sh call site.
  - [x] Add a `verify-runbook` block AFTER `verify-symbolication.sh` (parallel call). Inline shell — the logic is short:
    ```bash
    echo "→ Verify post-deploy runbook fingerprint"
    expected_fp=$(cat infra/.runbook-fingerprint)
    actual_fp=$(curl -fsS "${PORTAL_URL:-https://3d.ezop.ddns.net}/agent-runbook" \
      | awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' \
      | sha256sum | awk '{print $1}')
    if [ "$expected_fp" = "$actual_fp" ]; then
      echo "✓ runbook fingerprint OK ($actual_fp)"
      echo "OK $(date -Iseconds) $actual_fp" > infra/.last-verify-runbook
    else
      echo "WARN runbook fingerprint mismatch — expected $expected_fp, got $actual_fp" >&2
      echo "FAILED $(date -Iseconds) expected=$expected_fp actual=$actual_fp" > infra/.last-verify-runbook
    fi
    ```
  - [x] Non-fatal: do NOT exit non-zero on mismatch (mismatch is a warning, not a deploy-blocker — same pattern as `verify-symbolication.sh`).
  - [x] Add `infra/.last-verify-runbook` to `.gitignore` if not already there (it's a state marker, not source).

- [x] **Task 6: Smoke-test locally** (AC: 8)
  - [x] After build, `curl http://192.168.2.190:8090/agent-runbook` (LAN HTTP) returns 200 + markdown.
  - [x] If using `docker compose up` locally (not on .190), use `curl http://localhost:8000/agent-runbook` instead — the API container exposes 8000 internally.

- [x] **Task 7: Run full test suite** (AC: ruff + pytest)
  - [x] `ruff check apps/api` — passes.
  - [x] `ruff format apps/api --check` — passes (run `ruff format` to auto-fix if not).
  - [x] `pytest apps/api/tests` — 424+ tests pass; no new regressions.
  - [x] `apps/api/tests/test_openapi_agent_surface.py` — 24 tests still pass; new `/agent-runbook` route is OUT of scope for that test (different tag).

- [x] **Task 8: Commit + auto-deploy** (AC: 10)
  - [x] Stage: `apps/api/app/modules/runbook/__init__.py`, `apps/api/app/modules/runbook/router.py`, `apps/api/app/router.py` (mount), `apps/api/Dockerfile`, `infra/nginx-180/3d-portal.conf`, `infra/scripts/deploy.sh`, `.gitignore` (if changed).
  - [x] Conventional commit `feat(api): /agent-runbook route + deploy fingerprint verify (E4.2)`.
  - [x] Auto-deploy via `infra/scripts/deploy.sh`. Verify pass for both symbolication AND runbook fingerprint. The runbook fingerprint MUST match baseline `49280ada...` since intro was untouched.

- [x] **Task 9: Sync nginx edge config** (AC: 4)
  - [x] After portal deploy lands, `cd ~/repos/configs/` and run that repo's deploy/sync mechanism for the nginx change.
  - [x] Test prod URL: `curl https://3d.ezop.ddns.net/agent-runbook | head -3` returns the H1 + intro paragraph.
  - [x] If the edge sync requires manual operator intervention (e.g. `sync.sh` needs SSH key prompt), surface that — don't pretend it auto-ran.

- [x] **Task 10: Smoke-test on prod** (AC: 9)
  - [x] `curl https://3d.ezop.ddns.net/agent-runbook | wc -l` ≥ 100 (runbook is 295 lines as of last update).
  - [x] `curl -I https://3d.ezop.ddns.net/agent-runbook` shows `Content-Type: text/markdown; charset=utf-8`.
  - [x] `curl https://3d.ezop.ddns.net/agent-runbook | awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' | sha256sum` matches the file in `infra/.runbook-fingerprint`.

## Dev Notes

### Code-side references

- Existing module structure to mirror: `apps/api/app/modules/admin/router.py` (3 routes, simple) or `apps/api/app/modules/sot/router.py` (6 routes). Both use `APIRouter(prefix=..., tags=[...])` + `@router.get(...)`.
- `apps/api/app/main.py:create_app()` — central app factory; this is where the runbook router needs to be `app.include_router(runbook_router)`'d at root level (NOT under the `/api`-prefixed `api_router`).
- `apps/api/app/router.py` — the `/api`-prefixed sub-router that aggregates module routers. The runbook router does NOT go here.
- `apps/api/Dockerfile` — multi-stage build. The COPY needs to be in the runtime stage (`final` or similar), not just the builder.
- `infra/docker-compose.yml` — confirm the `api` service `build.context` is the repo root (or at least includes `docs/`).
- `infra/scripts/deploy.sh` — the verify-symbolication.sh call site is the integration point for the runbook verify. Read the script first to find the exact line.
- `infra/nginx-180/3d-portal.conf` — match the existing `location /api/ { proxy_pass http://api; }` pattern. The runbook needs a similar block but with `/agent-runbook` path.

### Anti-patterns to actively prevent

- ❌ **Don't mount the runbook router under `/api/` prefix.** The path is `/agent-runbook` at the root, NOT `/api/agent-runbook`. Mounting via `api_router` (which has `prefix="/api"`) would yield `/api/agent-runbook` — wrong.
- ❌ **Don't read the runbook from `docs/agents-add-model-runbook.md` at request time** (i.e. don't use the source-tree path). The Dockerfile COPY puts it at `/app/static/agent-runbook.md` — read from there. This guarantees image-deploy atomicity (runbook version-locks with API code).
- ❌ **Don't add auth to `/agent-runbook`** per Decision B. The runbook documents authentication; gating it on auth creates a chicken-and-egg.
- ❌ **Don't return 404 if the file is missing** — return 503 (deploy bug, not "doesn't exist"). 404 would suggest the route is unreachable, which is not the case.
- ❌ **Don't hard-code the fingerprint extraction chain inline** in deploy.sh as something different from Story 4.1's chain. Use the EXACT awk filter from Story 4.1's Completion Notes: `awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}'`. Any deviation produces fingerprint mismatch on a runbook that hasn't actually changed.
- ❌ **Don't make the verify a deploy-blocker.** Mismatch yields stderr warning + state marker, not non-zero exit. Same as `verify-symbolication.sh`.
- ❌ **Don't forget the configs/nginx sync.** The portal repo's deploy.sh does NOT touch the edge proxy. Sync to `~/repos/configs/nginx/` is a separate manual step (or via that repo's sync.sh).
- ❌ **Don't change the runbook intro paragraph** in this commit. Fingerprint MUST match baseline `49280ada...` post-deploy. If it doesn't match, something silently mutated the runbook (whitespace, BOM, line ending) and that's a real bug to investigate, not silently update the fingerprint.

### Project Structure Notes

- New module `apps/api/app/modules/runbook/` follows the established pattern (sibling to `admin/`, `sot/`, `auth/`, `share/`).
- `infra/.last-verify-runbook` is a NEW state marker file (sibling to `infra/.last-verify` from Initiative 1). Both are gitignored — operator state, not source.
- `~/repos/configs/nginx/3d-portal.conf` is OUT of this repo entirely — that's the cross-repo coordination point.

### References

- [_bmad-output/planning-artifacts/epics.md § Story 4.2](../planning-artifacts/epics.md) lines 704-727 (this story's spec).
- [_bmad-output/planning-artifacts/architecture.md § Decision A + B + D](../planning-artifacts/architecture.md) lines 878-918 (delivery via FastAPI route, public read, fingerprint discipline).
- [_bmad-output/implementation-artifacts/4-1-agents-add-model-runbook.md § Completion Notes](4-1-agents-add-model-runbook.md) — fingerprint extraction chain (BINDING).
- [_bmad-output/project-context.md § Deploy](../project-context.md) — auto-deploy rule + edge proxy lives in `~/repos/configs/`.
- [apps/api/app/main.py](../../apps/api/app/main.py) — app factory; runbook router mount point.
- [apps/api/app/router.py](../../apps/api/app/router.py) — `/api`-prefixed sub-router (NOT where runbook goes).
- [apps/api/Dockerfile](../../apps/api/Dockerfile) — runtime image; COPY runbook here.
- [infra/scripts/deploy.sh](../../infra/scripts/deploy.sh) — verify chain integration point.
- [infra/nginx-180/3d-portal.conf](../../infra/nginx-180/3d-portal.conf) — local nginx config; sync to `~/repos/configs/nginx/`.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context). Single-pass dev + Codex review + fix-up, 2026-05-11 (autonomous mode).

### Completion Notes List

- **Live URL works end-to-end:** `curl https://3d.ezop.ddns.net/agent-runbook` returns 200 + `text/markdown; charset=utf-8` + 295 lines. Fingerprint matches baseline `49280ada...` post both deploy runs.
- **Discovered during dev:** the in-repo `infra/nginx-180/3d-portal.conf` is OUT OF DATE vs the live edge config (`~/repos/configs/nginx/3d.ezop.ddns.net.conf` — note different filename). Live edge is simpler — IP allowlist (192.168.2.0/24 + 10.8.0.0/24), no basic-auth, simple catch-all proxy to .190:8090. The in-repo mirror is documentation-quality, not actually deployed. Did NOT sync the in-repo update to `~/repos/configs/` since the live edge already routes `/agent-runbook` correctly via the catch-all + my new `apps/web/nginx.conf` block. Flagged as a follow-up doc-hygiene task: either reconcile `infra/nginx-180/3d-portal.conf` with the real prod config OR archive it.
- **Dockerfile context shift:** `apps/api/Dockerfile` build context moved from `apps/api/` to repo root so it can COPY both `apps/api/*` and `docs/agents-add-model-runbook.md`. Followed the pattern already established by `workers/render/Dockerfile` (which uses the same context shift). All `apps/api/` COPY paths were prefixed accordingly. Codex P2 follow-up: added root `.dockerignore` to prevent `.git`, `infra/.env`, `_bmad-output/`, `node_modules/` etc. from leaking into the build context.
- **Two-layer nginx routing chain** for `/agent-runbook`:
  1. Edge (`~/repos/configs/nginx/3d.ezop.ddns.net.conf`): catch-all `location /` proxies everything to `192.168.2.190:8090` (web container). Already in place; no edit needed.
  2. Web container (`apps/web/nginx.conf`): NEW `location /agent-runbook` block proxies to `api:8000` via Docker DNS variable (matching the existing `/api/` pattern). Must precede the SPA fallback `location /`.
- **deploy.sh non-fatal verify** required restructuring under `set -euo pipefail`: original code did `actual_fp="$(curl ... | ...)"` which would kill the whole deploy on any curl failure. Codex P1 fix: capture curl exit explicitly via `|| curl_exit=$?`, branch on exit-code + body, write OK / SKIPPED / FAILED state marker in every branch.
- **Content-Type sanity check** added to deploy verify per Codex P3: a wrong 200 response with wrong body (e.g. SPA fallback HTML reaching the route by mis-routing) now FAILs verify rather than coincidentally hashing a non-runbook intro paragraph.
- **5 new pytest cases** for the route contract (200 + Content-Type + no-auth + root-mount + 503-on-missing-file + OpenAPI metadata). Total backend tests: 429.
- **Auto-deploy fired twice** (initial commit `9ac52f6` + Codex fix-up `565b347`); both runs: symbolication verify ✓ + runbook fingerprint verify ✓ (release `0.1.0+565b347`).

### File List

- `apps/api/app/modules/runbook/__init__.py` (NEW)
- `apps/api/app/modules/runbook/router.py` (NEW)
- `apps/api/app/main.py` (MODIFIED — mount runbook_router at root)
- `apps/api/Dockerfile` (MODIFIED — context shifted to repo root, COPY paths updated, runbook COPY added)
- `apps/web/nginx.conf` (MODIFIED — new `location /agent-runbook` block)
- `infra/docker-compose.yml` (MODIFIED — api + arq-worker context shift)
- `infra/nginx-180/3d-portal.conf` (MODIFIED — added `location /agent-runbook` to in-repo mirror; live edge catch-all already covers this)
- `infra/scripts/deploy.sh` (MODIFIED — runbook fingerprint verify block; restructured for non-fatal under set -e)
- `.gitignore` (MODIFIED — adds `infra/.last-verify-runbook`)
- `.dockerignore` (NEW — Codex P2 fix; protects build context after repo-root shift)
- `apps/api/tests/test_runbook.py` (NEW — 5 contract tests; Codex P3 fix)

### Change Log

- 2026-05-11 — Initial commit `9ac52f6` on `main`. Auto-deployed; symbolication verify ✓; runbook fingerprint verify ✓.
- 2026-05-11 — Codex review of `9ac52f6` returned 1 P1 + 1 P2 + 2 P3. All addressed in commit `565b347`. Auto-deployed; both verify steps ✓ (release `0.1.0+565b347`). Status `ready-for-dev → in-progress → review → done`.

### Senior Developer Review (AI)

**Reviewer:** Codex (codex-cli 0.129.0) via `codex exec`
**Date:** 2026-05-11
**Commit reviewed:** `9ac52f6` (initial)
**Outcome:** Changes Requested → addressed in `565b347`

#### Action Items

- [x] **[P1]** `deploy.sh` runbook verify dies on curl fail under `set -euo pipefail` — never writes the FAILED marker. **Resolution:** restructured with explicit `curl_exit` capture + branch on exit code; OK / SKIPPED / FAILED marker always written. (`565b347`)
- [x] **[P2]** No root `.dockerignore` after build-context shift — `.git`, `infra/.env`, `_bmad-output/`, `node_modules/` were being shipped to docker daemon. **Resolution:** root `.dockerignore` denies these by directory + allowlists `apps/api/*`, `workers/render/*`, and the agent runbook markdown. (`565b347`)
- [x] **[P3]** Verify doesn't check Content-Type (NFR7). **Resolution:** `curl -w '%{content_type}'` capture + `text/markdown*` prefix assertion before fingerprint extraction. (`565b347`)
- [x] **[P3]** Missing API regression test for route contract. **Resolution:** new `apps/api/tests/test_runbook.py` with 5 cases (200/Content-Type/no-auth/root-mount/503/OpenAPI). (`565b347`)

#### Review Mechanics Notes

- The P1 was the highest-quality finding: it's a subtle interaction between `set -e` and command-substitution exit-propagation that's easy to miss when copy-pasting from elsewhere. Cost: a single failed prod curl would kill the entire deploy script before writing the `infra/.last-verify-runbook` FAILED marker — defeating the three-signal model the entire verify chain is built on. Catching this BEFORE first failure is the correct trust calibration.
- The P2 (.dockerignore) is a security + speed win: every future build now ships dramatically less context. Codex correctly noticed the build-context shift had REMOVED the protection that `apps/api/.dockerignore` (if it existed) would have provided.
- Codex confirmed the live edge config check independently — flagged the in-repo `infra/nginx-180/3d-portal.conf` is documentation-quality vs `~/repos/configs/nginx/3d.ezop.ddns.net.conf` being the real prod config. Aligns with my own discovery.
