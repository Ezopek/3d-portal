# Operations Runbook

> **Note:** Several scripts referenced in this runbook (`infra/scripts/deploy.sh`, `infra/scripts/backup-sqlite.sh`, `infra/scripts/gen-htpasswd.sh`) and the production stack are introduced in Phase 12 of the implementation plan and may not exist yet. These instructions reflect the intended deployment workflow.

## Deploy to `.190`

```bash
bash infra/scripts/deploy.sh
```

This script builds images locally, ships them to `.190` via SSH, restarts the docker-compose stack, and runs alembic migrations to bring the schema in sync.

## Catalog (post-SoT)

The portal's source of truth is now the `portal.db` SQLite database on `.190` plus the `portal-content` volume. Models, files, tags, categories, notes, prints, and external links are managed through the admin API (`/api/admin/*`) and reverse-synced from WSL via the agent token + `scripts/hydrate_local_tree.py` (see SoT migration section below). The legacy one-way Windows → `.190` rsync is no longer used.

## First-time setup

**1. Generate htpasswd**

```bash
bash infra/scripts/gen-htpasswd.sh portal '<household-password>'
```

This creates the basic-auth file for nginx to use.

**2. Copy nginx config**

```bash
cp infra/nginx-180/3d-portal.conf ~/repos/configs/nginx/
cd ~/repos/configs && bash sync.sh
```

This deploys the edge proxy config to `.180` and reloads nginx.

**3. Generate JWT secret**

```bash
openssl rand -hex 32
```

Store this in `.env.production` as `JWT_SECRET`.

**4. Create GlitchTip project**

See `~/repos/configs/docs/glitchtip-agent-guide.md` for how to create a new project in GlitchTip and get its DSN.

## Backup

SQLite database backup runs nightly via cron on `.190`:

```bash
infra/scripts/backup-sqlite.sh
```

Backups are stored in `/mnt/raid/3d-portal-state/backups/` with 30-day retention (e.g. `portal-2026-04-29.db`).

**Restore:** Stop the api container, copy the backup back into `/mnt/raid/3d-portal-state/portal.db`, and restart the compose stack.

## Failure modes

| Symptom | Check | Fix |
|---|---|---|
| `5xx on /api/models` | Check OpenSearch (OTel logs) `service.name=3d-portal-api` for trace | Inspect `docker compose logs api`; database volume must be mounted at `/data/state/portal.db` |
| Share link returns `401` | Confirm `/share/*` and `/api/share/*` bypass blocks present in `~/repos/configs/nginx/3d-portal.conf` | Re-deploy nginx config via `bash sync.sh` in configs repo |
| Render stuck on "running" | Inspect arq worker logs with `docker compose logs worker` | Restart worker; status TTL is 1h so it self-clears |

## Routine operations

**Log in to admin panel**

Open `/login` and use `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env.production`.

**Revoke a share token**

Via the admin UI (share list, coming in Phase 8), or directly:

```bash
curl -X DELETE https://3d.ezop.ddns.net/api/admin/share/{token} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Retrigger a render**

```bash
curl -X POST https://3d.ezop.ddns.net/api/admin/models/{model_uuid}/render \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

The optional body field `selected_stl_file_ids: []` lets you pin which STLs participate (defaults to `ModelFile.selected_for_render` rows, falling back to the first STL).

**Bulk-enqueue renders for the whole catalog**

When deploying to a fresh content volume (no pre-rendered PNGs), enqueue render jobs for every model in one shot:

```bash
# Get a fresh JWT (admin login via /api/auth/login). Then:
bash infra/scripts/render-all.sh "<bearer-jwt>"
```

The script lists `/api/models`, then `POST /api/admin/models/{uuid}/render` for each. arq processes jobs serially in the worker container; wall time depends on STL complexity (~5–30 s per model on .190). Watch progress with `docker compose logs -f worker` on the host.

## GlitchTip observability — operator runbook

All three services (web, api, worker) report uncaught errors to a single GlitchTip project at `https://glitchtip.ezop.ddns.net`, project `3d-portal` in org `homelab`. The DSN is shared across services; events are tagged `service=web|api|render`, `release=<pkg.version>+<git_short_sha>`, `environment=$ENVIRONMENT`.

Frontend symbolication is fully wired as of Epic 3: `@sentry/vite-plugin` injects debug IDs at build time INSIDE the docker stage, source maps upload via chunk-upload, and `verify-symbolication.sh` proves on every deploy that the resolved top frame still matches `^apps/web/src/.+\.tsx?$`.

### Configuration

The DSN lives in two `.env` files:

| Where | Vars | Why |
|---|---|---|
| `.190:/mnt/raid/docker-compose/3d-portal/.env` | `SENTRY_DSN`, `VITE_SENTRY_DSN` | passed to api/worker containers (runtime) and web (build arg) |
| `~/repos/3d-portal/infra/.env` (dev box only) | `SENTRY_DSN`, `VITE_SENTRY_DSN`, `GLITCHTIP_AUTH_TOKEN`, `GLITCHTIP_ORG_SLUG`, `GLITCHTIP_PROJECT_SLUG` | the auth token + slugs power the in-build plugin upload, the CLI manual recovery, and the verify ritual; must NOT be pushed to `.190` |

If the DSN is rotated or the project recreated, update both `.env` files (the public DSN value is identical) and re-deploy. Replacing the auth token is dev-box-only.

### Deploy ritual

`bash infra/scripts/deploy.sh` runs the canonical chain:

1. **Build images locally** — `docker compose build` with `DOCKER_BUILDKIT=1`. Inside the `apps/web` build stage, `@sentry/vite-plugin` injects debug IDs into the bundle and uploads source maps via the chunk-upload protocol against `http://192.168.2.190:8800` (LAN HTTP, mandatory for multi-MB chunks). `SENTRY_AUTH_TOKEN` flows in via BuildKit `--mount=type=secret,id=sentry_token,required=true` — token never lands in any image layer (verifiable with `docker history`).
2. **Save and ship** — `docker save | ssh ... docker load` pushes images to `.190`.
3. **Restart stack** — `docker compose up -d` recreates containers.
4. **Alembic migrations** — `docker compose run --rm api alembic upgrade head`.
5. **Verify post-deploy symbolication** — `bash infra/scripts/verify-symbolication.sh` triggers a smoke event via headless Chrome against `https://3d.ezop.ddns.net/?__sentry_smoke=<uuid>`, polls GlitchTip REST for the resolved event, asserts the top frame regex `^apps/web/src/.+\.tsx?$`, and writes `infra/.last-verify` (single-line tab-separated `<ISO-8601>\t<STATUS>\t<release>`).

The verify call is **non-fatal**: deploy.sh exits 0 regardless of verify outcome. The verify result lands in three independent signals (the three-signal failure model — NFR-R3):

- **stdout/stderr warning** — `✓ verify OK` on success (stdout) or red `⚠ verify FAILED: <reason>` on failure (stderr), exit-code-mapped per `verify-symbolication.sh`'s FR12 contract (exit 0/1/2/3/4).
- **`infra/.last-verify` marker** — `OK` on success, `FAILED` on any non-zero exit. Consumed by the next deploy's stale-verify tripwire (see below).
- **Synthetic GlitchTip event** — for exit codes 1 (regex mismatch) and 3 (auth/scope failure), `verify-symbolication.sh` POSTs an envelope event tagged `deploy.verification=failed` to the same DSN as runtime errors. Operator sees it in the same triage path; filter by tag to distinguish meta-failures from real app exceptions.

**Stale-verify tripwire.** At the START of every `deploy.sh` invocation (before the build phase), the script reads `infra/.last-verify` mtime and compares it to HEAD's commit timestamp (`git log -1 --format=%ct HEAD`). If the marker is older than the current HEAD's commit time → a yellow `⚠ stale verify: previous deploy did not record a successful verification` warning prints to stderr (non-fatal). This guards against the "we forgot to run verify" decay scenario (FR16 / NFR-R4).

**Required tools on the dev box** (where `deploy.sh` runs): `docker`, `git`, `node` (via nvm; v22+ for the docker stage, v24+ on host), `jq`, `curl`, `uuidgen`, `timeout`, plus a headless Chrome/Chromium binary (`google-chrome` or `chromium`). The verify script auto-detects the browser; override with `HEADLESS_BROWSER=<binary>` if needed.

### Manual recovery — CLI fallback

When the in-build plugin upload fails (transient GlitchTip 5xx, network glitch, expired token mid-build, or the Phase 0 issue #299 redux), use `infra/scripts/upload-sourcemaps.sh` standalone:

```bash
cd /home/ezop/repos/3d-portal
set -a; source infra/.env; set +a
# Rebuild with maps in dist (the plugin's filesToDeleteAfterUpload removes them by default;
# disable the plugin or use a previously-built dist+maps archive — see the script's --help):
cd apps/web && npm run build && cd ../..
bash infra/scripts/upload-sourcemaps.sh
# Re-run verify to confirm the maps are now resolvable:
bash infra/scripts/verify-symbolication.sh
```

The CLI script uses the official `glitchtip-cli` (Rust, cached at `~/.cache/glitchtip-cli/`, sha256-pinned). It computes `RELEASE = ${pkg.version}+${git_short_sha}` from `apps/web/package.json` + `git rev-parse --short HEAD` — drift-impossible: matches both `apps/web/src/release.ts` (consumed by `Sentry.init`) and the in-build plugin's `release.name`. See `bash infra/scripts/upload-sourcemaps.sh --help` for the full operator guide.

**FR4 hard-fail policy.** If `SENTRY_AUTH_TOKEN` is missing or empty in `infra/.env`, the docker build aborts at the BuildKit secret-mount step (`required=true` + non-empty guard in `apps/web/Dockerfile`). NO silent skip — the deploy stops before any image ships. Either set the token or roll back to a previous deploy.

### Token rotation procedure (same-day)

1. Open `https://glitchtip.ezop.ddns.net/profile/auth-tokens/` on LAN/VPN.
2. Click **+ Create New Token**. Set the scopes per the next subsection (5 scopes total).
3. Copy the new token value.
4. Update `~/repos/3d-portal/infra/.env`: replace the `GLITCHTIP_AUTH_TOKEN` value with the new token. Save (`chmod 600` already applied).
5. Validate end-to-end: `bash infra/scripts/deploy.sh`. The plugin upload + verify ritual both exercise the new token. A green `✓ verify OK` line + `infra/.last-verify` carrying `OK <release>` confirms the token works.
6. Revoke the OLD token in the GlitchTip UI.
7. Record the rotation date inline in this runbook (or in `_bmad-output/project-context.md` as an evergreen log entry).

**Why same-day:** the token has write scope (`event:write`, `project:write`). Quarterly rotation is the baseline; ad-hoc rotation on suspected leak / personnel change should complete within a single operator session.

### Required token scopes (exact list)

The token MUST carry exactly these five scopes:

| Scope | Used by |
|---|---|
| `org:read` | REST queries against `/api/0/organizations/<org>/...` |
| `project:read` | REST queries against `/api/0/projects/<org>/<proj>/...` |
| `project:write` | source-map upload (chunk-upload + assemble) |
| `project:releases` | release record creation/updates during plugin upload |
| `event:write` | `verify-symbolication.sh`'s synthetic alarm event POST (envelope endpoint) |

NOT `org:write`, NOT `org:admin`. Token-scope minimization is NFR-S3; broader scopes are a liability without value.

`event:write` is required by the verify ritual's three-signal failure path (Story 3.1's `emit_alarm` helper). A token that worked under the old 4-scope list will silently fail at the alarm-POST step on regex-mismatch failures — the alarm event won't ingest, leaving only stdout + the `.last-verify FAILED` marker as failure signals. The verify ritual's NFR-R3 three-signal contract requires the fifth scope.

### Triage script usage

> **Status (2026-05-10):** the triage script is Epic 2 scope and ships in **Story 2.5** (currently backlog). The contract below is locked; once the story lands, the section stays accurate.

```bash
bash infra/scripts/glitchtip-triage.sh <issue_id>
```

Returns a paste-ready markdown stub with fixed field order:

- Top frame (`filename:line`)
- Fingerprint
- Route context (`route.pathname`)
- `model.id` (when present)
- Release SHA + commit hash
- Last 5 events (timestamp + message preview)
- Suggested file to edit (top-frame source)
- GlitchTip permalink

Schema is verifiable: `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returns zero diff on stable contract. Read-only against GlitchTip — no state mutation.

The output is the triage interface for AI agents. Open it in `bmad-quick-dev` or `bmad-create-story` directly; the GlitchTip web UI is the slow path.

### Cross-references

- `~/repos/configs/docs/glitchtip-agent-guide.md` — REST recipes for arbitrary GlitchTip queries (events, issues, releases). Extends what this runbook covers.
- `~/repos/configs/docs/observability-logging-contract.md` — tag taxonomy (ECS-style dotted naming for `service.*`, `deployment.*`, `route.*`, etc.). Project-specific extensions preserve the dotted convention.
- `_bmad-output/planning-artifacts/architecture.md` Decision K — verify ritual rationale + three-signal failure model.

### GlitchTip 6.1.x version pin

The verify and CLI flows depend on the GlitchTip 6.1.x REST API surface:

- `GET /api/0/projects/<org>/<proj>/issues/?statsPeriod=5m&query=<tag>:<value>` — issue search by tag (verify ritual's poll target).
- `GET /api/0/issues/<id>/events/latest/` — latest event for an issue.
- `POST /api/0/organizations/<org>/chunk-upload/` + `POST /api/0/organizations/<org>/artifactbundle/assemble/` — modern source-map upload (chunk-upload protocol; replaces the legacy `releases/{version}/files/` endpoint, which returns 405 on this version).
- `POST /api/<project_id>/envelope/` — Sentry-protocol envelope ingest (synthetic alarm events).
- The `release` field surfaces in event JSON as a TAG entry (`.tags[] | select(.key=="release")`), NOT as a top-level `.release` field.

Upgrade to GlitchTip 7.x requires re-validation of all five surfaces (NFR-I1) before re-tagging the runbook. Cite the "Provisioning a fresh project" subsection below for the operator-side test plan; cross-check against the live verify ritual after upgrade.

**Homelab GlitchTip config invariant.** The `glitchtip-worker` container in `/mnt/raid/docker-compose/glitchtip.yml` MUST mount the `glitchtip-uploads` volume at `/code/uploads` — same as the web container. Without it, `assemble_artifacts_task` fails with `FileNotFoundError` and source maps never persist in `sourcecode_debugsymbolbundle`. Discovered + fixed during Story 3.1's dev cycle (2026-05-09); see `_bmad-output/implementation-artifacts/epic-1-symbolication-regression.md` for full context.

### Trigger a test event

API (deliberate `RuntimeError`, admin-only):

```bash
source infra/.env
TOKEN=$(curl -fsS -X POST http://192.168.2.190:8090/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -i -X POST http://192.168.2.190:8090/api/admin/sentry-test \
  -H "Authorization: Bearer $TOKEN"
```

Returns 500. The event lands in GlitchTip within ~5 s tagged `service=api`, `release=$PORTAL_VERSION`, `environment=production`. The `Authorization` header is scrubbed to `[Filtered]` (verify by clicking into the issue).

Worker: enqueue a render for a model whose STL file is missing on disk (e.g. the row exists in `model_file` but the file under `portal-content/` was deleted out-of-band). The catch-all `except Exception` in `render_model` calls `sentry_sdk.capture_exception` once per failure.

Frontend: open `http://192.168.2.190:8090` in a browser, open DevTools console, run `throw new Error("frontend-test")`. Visible in the panel within seconds tagged `service=web`.

### Reading recent issues from CLI

```bash
source infra/.env
curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "https://glitchtip.ezop.ddns.net/api/0/projects/$GLITCHTIP_ORG_SLUG/3d-portal/issues/?statsPeriod=24h" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    print(f\"[{i['level']}] {i['title']} (count: {i['count']}, last: {i['lastSeen']})\")
"
```

To filter by service:

```bash
... "?statsPeriod=24h&query=service:render" ...
```

### Provisioning a fresh project

If the project ever needs to be recreated (new instance, lost DB, etc.):

1. Read GlitchTip admin creds from `.190:/mnt/raid/docker-compose/glitchtip.env` (`DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`).

2. The login endpoint uses django-allauth headless API. Fetch the CSRF cookie first:

```bash
curl -s -c /tmp/gt-cookies.txt https://glitchtip.ezop.ddns.net/_allauth/browser/v1/config >/dev/null
CSRF=$(grep csrftoken /tmp/gt-cookies.txt | awk '{print $7}')

curl -s -b /tmp/gt-cookies.txt -c /tmp/gt-cookies.txt \
  -X POST https://glitchtip.ezop.ddns.net/_allauth/browser/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "Referer: https://glitchtip.ezop.ddns.net" \
  -H "Origin: https://glitchtip.ezop.ddns.net" \
  -H "X-CSRFTOKEN: $CSRF" \
  -d '{"email":"<EMAIL>","password":"<PASSWORD>"}'
```

3. With the session cookie, list orgs/teams and create the project:

```bash
CSRF=$(grep csrftoken /tmp/gt-cookies.txt | awk '{print $7}')
curl -s -b /tmp/gt-cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -H "X-CSRFTOKEN: $CSRF" \
  -H "Referer: https://glitchtip.ezop.ddns.net" \
  https://glitchtip.ezop.ddns.net/api/0/teams/<ORG>/<TEAM>/projects/ \
  -d '{"name":"3d-portal","platform":"javascript-react"}'
```

4. Get the DSN:

```bash
curl -s -b /tmp/gt-cookies.txt -H "X-CSRFTOKEN: $CSRF" -H "Referer: https://glitchtip.ezop.ddns.net" \
  https://glitchtip.ezop.ddns.net/api/0/projects/<ORG>/3d-portal/keys/ \
  | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['dsn']['public'])"
```

5. For sourcemap uploads + verify alarm POSTs, use any existing long-lived API token from `https://glitchtip.ezop.ddns.net/profile/auth-tokens/` with the exact 5-scope list documented in **Required token scopes** above (`org:read`, `project:read`, `project:write`, `project:releases`, `event:write`). Save as `GLITCHTIP_AUTH_TOKEN` in local `infra/.env`.

## SoT migration — operational state (post Slice 2 series)

**As of 2026-05-05**, the SoT migration (Slices 2A-2D) is done AND the
UI rewrite (Slices 3A-3F) is done. The portal database on `.190` now
holds the canonical catalog: 89 models, 821 binary files (2.8 GB across
`/mnt/raid/3d-portal-content/`), 243 deduplicated tags, 43 categories,
62 external links, 31 notes, 26 print records. The frontend at
`https://3d.ezop.ddns.net/` consumes only `/api/*` (the SoT surface).

**Legacy cleanup completed on 2026-05-06**: `/api/catalog/*`,
`/api/files/*`, `/api/admin/refresh-catalog`,
`/api/admin/render/{string-id}`, the legacy thumbnail-override
endpoints, `CatalogService`, the `thumbnailoverride` and
`renderselection` tables, and the WSL `sync-data.sh` script were all
removed once log inspection confirmed zero non-test callers.

**E4.4-followup (2026-05-11) retired the migration scripts entirely.**
`Model.legacy_id` was dropped via Alembic migration `0010_drop_model_legacy_id.py`;
`scripts/migrate_from_index_json.py`, `scripts/backfill_legacy_renders.py`,
`scripts/backfill_iso_thumbnail.py`, and `scripts/fix_legacy_render_names.py`
were `git rm`'d. Disaster recovery references the pre-DROP snapshot at
`docs/migration-reports/2026-05-11-legacy-id-snapshot.json` (89 rows,
~5 KB) for the legacy-id ↔ model.id mapping; full re-import from a
Nextcloud snapshot would have to be reconstructed manually (or by
checking out commit `d92e551` — the original SoT migration entry
point — from git history).

### UI rewrite delivered (Slices 3A-3F)

- **3A — Auth + API context.** `AuthContext` + `useAuth()` hook. `GET /api/auth/me` accepts any authenticated role. SoT TypeScript types in `apps/web/src/lib/api-types.ts`.
- **3B — List view rebuild.** `CategoryTreeSidebar` (recursive expandable tree) + `FilterRibbon` (search, tag chips, status, source, sort). Server-side filters and offset/limit pagination. `/api/models` extended with `category_ids[]`, `tag_ids[]` (AND), `source`, `sort` enum.
- **3C — Detail view rebuild.** Product-style layout: `ModelHero` + `ModelGallery` (4:3 ~36% width) + content rail (`DescriptionPanel`, `ExternalLinksPanel`, `MetadataPanel`) + `SecondaryTabs` (Files STL-primary / Prints / Operational notes).
- **3D — Photos manager + DnD.** Admin-only `PhotosTab` (master-detail) with `@dnd-kit/sortable` reorder, set-thumbnail, delete, drag-drop upload. Backend `position` column on `model_file` + `POST /api/admin/models/{id}/photos/reorder`.
- **3E — Edit affordances.** Status / rating popovers (atomic). Side-sheets: description, tags (with create-new), prints, notes. Delete-model confirmation modal (typed-name confirm). All ✏ icons wired on Hero/DescriptionPanel/PrintsTab/OperationalNotesTab.
- **3F — Cleanup + ActivityTab.** Audit-log read endpoint `GET /api/admin/audit-log`. Admin-only `ActivityTab` showing per-model audit feed. Deleted orphan legacy frontend code (share view, gallery utilities, dead types, dead lib helpers).

### Active surfaces

- **Public read** (`/api/categories`, `/api/tags`, `/api/models`,
  `/api/models/{id}`, `/api/models/{id}/files`,
  `/api/models/{id}/files/{id}/content`) — serves real DB-backed data.
- **Admin write** (`/api/admin/*` for models, files, tags, categories,
  notes, prints, external_links) — JWT-protected; admin role plus the
  newly-enabled `agent` role can both call most endpoints.
  Hard-delete (`?hard=true`) is admin-only.
- **Share** (`/api/share/{token}` public; `/api/admin/share` admin
  CRUD) — UUID-based, reads from SoT entity tables; no legacy
  file-based path remains.

### Agent service account

A user `agent@portal.example.com` exists on `.190` with role=`agent`.
Provisioned via `python -m scripts.bootstrap_agent --email ... [--rotate]`.
Local credentials cached at `~/.config/3d-portal/agent.token` (chmod 600);
the `hydrate_local_tree.py` script reads it for re-auth.

### Reverse-sync

Run `python -m scripts.hydrate_local_tree --portal-url
http://192.168.2.190:8090 --target <local-dir> --token-file
~/.config/3d-portal/agent.token --kinds stl` from WSL to materialize
STLs locally. State is kept in `<target>/.hydrate-state.json` for
incremental updates. Layout:
`<category-slug>/<subcategory-slug>/<model-slug>-<8-char-uuid>/<original_name>`
(the 8-char suffix is the model UUID hex with dashes stripped,
truncated). **Note:** prior to E4.4-followup (2026-05-11) the suffix
was `legacy_id` (e.g. `001`, `002`) where present, falling back to the
short-uuid; post-DROP all models use the short-uuid uniformly.
Local trees rendered under the old scheme retain their pre-rename
directory names — either accept the layout change on next re-hydrate
OR run a one-time bulk-rename pass against the local tree before
re-running `hydrate_local_tree.py`.

### What remains

- **`audit_log.action` enum tightening** — currently the column is free
  `text`. The `KNOWN_ENTITY_TYPES` runtime guard prevents drift; future
  polish slice can convert to a strict `AuditAction` enum once the API
  mutation catalog stops growing.
- **3MF originals staging dir** — the migration imported from
  `/mnt/raid/3d-portal-staging/3mf-originals/` (300 MB). Removable.

### UI deferrals (post-3F follow-ups, not blocking)

- **Full-page `/admin/models/new`** for creating a model from scratch.
  Admin can use the API or the migration script in the meantime; the
  agent does most creates anyway.
- **`/admin/users` page** for member provisioning. Use direct SQL or
  the bootstrap script until then.
- **Side-sheets for ExternalLinks, Category picker, File metadata.**
  These edit paths are low-frequency; the API supports them directly.
- **Share view rebuild.** The share-create UI was deleted with the dead
  `ShareDialog`; resurrect both when sharing becomes a real flow.
- **Description "view source" toggle.** Source-original is currently
  overwritten in place; storing it separately would require a DB
  convention decision (column on `Model` or a flagged `ModelNote`).
- **Backup for `portal-content/`** — restic schedule per spec section 7.1.
