# Operations Runbook

> **Note:** Several scripts referenced in this runbook (`infra/scripts/deploy.sh`, `infra/scripts/sync-data.sh`, `infra/scripts/backup-sqlite.sh`, `infra/scripts/gen-htpasswd.sh`) and the production stack are introduced in Phase 12 of the implementation plan and may not exist yet. These instructions reflect the intended deployment workflow.

## Deploy to `.190`

```bash
bash infra/scripts/deploy.sh
```

This script builds images locally, ships them to `.190` via SSH, restarts the docker-compose stack, and runs alembic migrations to bring the schema in sync.

## Sync catalog

From WSL, after editing the catalog:

```bash
bash infra/scripts/sync-data.sh
```

This uses rsync over SSH to copy new/modified models from Windows to `.190`, then triggers the API to refresh its in-memory caches. For a safety net, add this to your WSL crontab to run every 15 minutes:

```
*/15 * * * * bash ~/repos/3d-portal/infra/scripts/sync-data.sh
```

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
| `5xx on /api/catalog/models` | Check OpenSearch (OTel logs) `service.name=3d-portal-api` for trace | Likely `index.json` parse failure or volume not mounted; check docker-compose logs and volume mounts |
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
curl -X POST https://3d.ezop.ddns.net/api/admin/render/{model_id} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Force catalog refresh**

```bash
curl -X POST https://3d.ezop.ddns.net/api/admin/refresh-catalog \
  -H "Authorization: Bearer $JWT_TOKEN"
```

This is also called automatically by `infra/scripts/sync-data.sh` after an rsync completes.

**Bulk-enqueue renders for the whole catalog**

When deploying to a fresh data volume (no pre-rendered PNGs), enqueue render jobs for every model in one shot:

```bash
# Get a fresh JWT (admin login via /api/auth/login). Then:
bash infra/scripts/render-all.sh "<bearer-jwt>"
```

The script lists `/api/catalog/models`, then `POST /api/admin/render/{id}` for each. arq processes jobs serially in the worker container; wall time depends on STL complexity (~5–30 s per model on .190). Watch progress with `docker compose logs -f worker` on the host.

## GlitchTip error tracking

All three services (web, api, worker) report uncaught errors to a single GlitchTip project at `https://glitchtip.ezop.ddns.net`, project `3d-portal` in org `homelab`. The DSN is shared across services; events are tagged `service=web|api|render`, `release=$PORTAL_VERSION`, `environment=$ENVIRONMENT`.

### Configuration

The DSN lives in two `.env` files:

| Where | Vars | Why |
|---|---|---|
| `.190:/mnt/raid/docker-compose/3d-portal/.env` | `SENTRY_DSN`, `VITE_SENTRY_DSN` | passed to api/worker containers (runtime) and web (build arg) |
| `~/repos/3d-portal/infra/.env` (dev box only) | `SENTRY_DSN`, `VITE_SENTRY_DSN`, `GLITCHTIP_AUTH_TOKEN`, `GLITCHTIP_ORG_SLUG`, `GLITCHTIP_PROJECT_SLUG` | the auth token + slugs power `infra/scripts/upload-sourcemaps.sh` and must NOT be pushed to `.190` |

If the DSN is rotated or the project recreated, update both `.env` files (the public DSN value is identical) and re-deploy. Replacing the auth token is dev-box-only.

### Sourcemap upload (frontend symbolication)

`infra/scripts/deploy.sh` calls `infra/scripts/upload-sourcemaps.sh` after the docker web image is built. The upload script extracts `dist/` from the just-built `portal-web:$PORTAL_VERSION` image (so the bundle hashes match what `.190` will serve), then uses the official `glitchtip-cli` (cached binary in `~/.cache/glitchtip-cli/`) to upload via the chunk-upload protocol.

The legacy `POST /api/0/organizations/{org}/releases/{version}/files/` endpoint is NOT used — this GlitchTip version returns 405 there. Modern symbolication is debug-id-based; the CLI stores artifacts as debug-id-keyed bundles via `POST /api/0/organizations/{org}/chunk-upload/`.

The script uses `http://192.168.2.190:8800` (internal HTTP, GlitchTip pod port) instead of `https://glitchtip.ezop.ddns.net` to bypass the public nginx body-size limit on multi-MB sourcemap chunks. This means the upload only works from the dev box on the LAN.

To upload manually after a hotfix or release tag bump:

```bash
cd /home/ezop/repos/3d-portal
set -a; source infra/.env; set +a
# Build (or extract dist/ from a deployed image — see upload-sourcemaps.sh for that flow):
pnpm --dir apps/web build
bash infra/scripts/upload-sourcemaps.sh
```

If `GLITCHTIP_AUTH_TOKEN` is missing from `infra/.env`, the deploy still succeeds with sourcemap upload skipped (warning on stdout).

#### Known limitation: synthetic test events do not symbolicate

Vite's `build.sourcemap = "hidden"` does NOT inject a `//# debugId=` comment into the bundle. GlitchTip's chunk-upload symbolicator matches by debug-id, so synthetic events sent via the DSN store endpoint with crafted `stacktrace.frames[].abs_path` will appear in the panel but their stack frames stay minified.

Real frontend errors triggered in a browser DO carry the SDK's `release` tag and Sentry's per-event `debug_meta` block, which gives the symbolicator enough context to resolve via legacy by-name fallback most of the time. If you need bulletproof symbolication, the proper fix is to add `@sentry/vite-plugin` to `apps/web/vite.config.ts` so debug IDs get injected at build time. That is currently out of scope; track it as a follow-up if minified browser stacks bite you in practice.

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

Worker: enqueue a render for any model after temporarily renaming `/mnt/raid/3d-portal-data/_index/index.json` on `.190`. The catch-all `except Exception` in `render_model` calls `sentry_sdk.capture_exception` once per failure. **Restore the index immediately** (the api will start failing reads otherwise).

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

5. For sourcemap uploads, use any existing long-lived API token from `https://glitchtip.ezop.ddns.net/profile/auth-tokens/` with scopes `org:read`, `project:read`, `project:write`, `project:releases`. Save as `GLITCHTIP_AUTH_TOKEN` in local `infra/.env`.

## SoT migration — operational state (post Slice 2 series)

**As of 2026-05-05**, the SoT migration (Slices 2A-2D) is done AND the
UI rewrite (Slices 3A-3F) is done. The portal database on `.190` now
holds the canonical catalog: 89 models, 821 binary files (2.8 GB across
`/mnt/raid/3d-portal-content/`), 243 deduplicated tags, 43 categories,
62 external links, 31 notes, 26 print records. The frontend at
`https://3d.ezop.ddns.net/` consumes only `/api/*` (the SoT surface);
the legacy `/api/catalog/*` router is still mounted but has zero
non-test callers.

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
- **Legacy file-based** (`/api/catalog/*`, `/api/files/*`) — left in
  place for the existing UI to continue working. Reads from
  `/mnt/raid/3d-portal-data/` (rsync target). Will be removed when the
  UI is rewritten to call the new endpoints.

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
incremental updates. Layout: `<category-slug>/<subcategory-slug>/<model-slug>-<legacy_id>/<original_name>`.

### What remains

- **Legacy `/api/catalog/*` router removal** — frontend no longer touches
  it, but the backend route + tests still exist. Pull the trigger after
  a short observation window (zero requests in logs); then disable the
  WSL `sync-data.sh` cron.
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
