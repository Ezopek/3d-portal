# 3d-portal — Agent Runbook

This runbook teaches an AI agent (Claude, Codex, or any future LLM) how to add a 3D model to the 3d-portal catalog from a source URL — Printables, Thangs, Thingiverse, MakerWorld, or Creality Cloud. It covers principles, the auth model, source-detection strategy, external-API recipes, the 3MF conversion procedure, the pre-flight checklist, and behavioral side-effects of the portal's API. Endpoint signatures, request/response schemas, and status codes are NOT in this document — they live in the auto-generated OpenAPI surface at `/api/openapi.json`, which pairs with this runbook.

## Principles

- **Pull-only ergonomics.** The portal serves discovery and accepts writes; it never pushes. The agent decides cadence — fetch this runbook + OpenAPI on demand, login once per session, reuse the cookie.
- **REST + cookie session.** All admin/sot calls go over HTTPS to `https://3d.ezop.ddns.net`. Auth is a JWT carried in the `portal_access` cookie set by the login endpoint. There is no long-lived bearer token; do NOT send `Authorization: Bearer ...` headers.
- **Idempotence.** Re-importing the same source URL must not duplicate models. Pre-flight check #4 (duplicate-check) gates this — query the existing catalog before creating.
- **Layered auto-discovery.** This runbook documents narrative, behavioral rules, and external-API recipes. The portal's own endpoints, request shapes, and status codes live in `/api/openapi.json` — query that, not source code.

## Auth & Login Flow

### Service account & credentials

The agent service account is a regular `User` row with `role=agent`, provisioned once on `.190` via `python -m scripts.bootstrap_agent --email agent@portal.local`. Credentials are a **password** (NOT a long-lived bearer token), stored on the agent host at `~/.config/3d-portal/agent.password`, mode `600`, owner `ezop`.

### Login (one-time per session)

Read the password inline and POST it to the login endpoint, capturing cookies into a jar:

```bash
pw=$(cat ~/.config/3d-portal/agent.password)
curl -s -c /tmp/portal-cookies.txt \
  -X POST \
  -H 'X-Portal-Client: web' \
  -H 'Content-Type: application/json' \
  -d '{"email":"agent@portal.local","password":"'"$pw"'"}' \
  https://3d.ezop.ddns.net/api/auth/login
```

The server responds with the user record in the body and sets two cookies:

- `portal_access` — `Path=/api`, `HttpOnly`, `Secure`, `SameSite=Strict`, JWT TTL ~10 min. Carries the principal for admin/sot calls.
- `portal_refresh` — `Path=/api/auth`, `HttpOnly`, `Secure`, `SameSite=Strict`, ~30-day TTL. Used only by the refresh endpoint.

### Reusing the cookie

All subsequent calls send the cookie jar back via `-b`. Mutations also need the CSRF header `X-Portal-Client: web`:

```bash
# Read (no CSRF header needed):
curl -s -b /tmp/portal-cookies.txt https://3d.ezop.ddns.net/api/categories

# Write (CSRF header required):
curl -s -b /tmp/portal-cookies.txt -c /tmp/portal-cookies.txt \
  -X POST \
  -H 'X-Portal-Client: web' \
  -H 'Content-Type: application/json' \
  -d '{"name_en":"Cali Cat","category_id":"<uuid>","source":"printables"}' \
  https://3d.ezop.ddns.net/api/admin/models
```

Pass `-c` on writes too so the cookie jar gets refreshed if the access cookie rolls over.

### Refresh (long sessions)

The access cookie expires after ~10 min. For sessions longer than that, call refresh (cheaper than re-reading the password); the refresh endpoint accepts the request as long as `portal_refresh` is still valid, even if the access cookie has already expired:

```bash
curl -s -b /tmp/portal-cookies.txt -c /tmp/portal-cookies.txt \
  -X POST -H 'X-Portal-Client: web' \
  https://3d.ezop.ddns.net/api/auth/refresh
```

Refresh tokens **rotate on every use** — replaying an old refresh cookie revokes the entire token family for the user. The `-c` write back into the same jar after every refresh is mandatory; do not snapshot a "spare" refresh cookie.

For batch / cron-style agents, the simpler model is to relogin once per run rather than juggle refresh.

### Rotation

When the password leaks or is suspected compromised, rotate on `.190`:

```bash
python -m scripts.bootstrap_agent --email agent@portal.local --rotate
```

The script prints the new password to stdout exactly once. Capture it and replace the file content on every host where the agent runs (`chmod 600` preserved). No service restart needed.

**Rotation alone is NOT sufficient against a captured cookie.** `--rotate` changes the password hash only; any `portal_refresh` cookie an attacker captured before rotation can still mint new access cookies for the rest of its ~30-day TTL. After every credential compromise, the operator must ALSO revoke all active refresh families for the agent user. The simplest path: relogin with the new password (which gives you a fresh cookie jar), then call the logout-all endpoint to revoke every OTHER family for the same user:

```bash
# 1) Relogin with the new password (overwrites the cookie jar with a fresh access+refresh pair)
pw=$(cat ~/.config/3d-portal/agent.password)
curl -s -c /tmp/portal-cookies.txt \
  -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
  -d '{"email":"agent@portal.local","password":"'"$pw"'"}' \
  https://3d.ezop.ddns.net/api/auth/login

# 2) Revoke every OTHER refresh family for this user (keeps the just-logged-in session)
curl -s -b /tmp/portal-cookies.txt -X POST -H 'X-Portal-Client: web' \
  https://3d.ezop.ddns.net/api/auth/logout-others
```

(Use `logout-all` instead of `logout-others` if you want to invalidate the current session too — useful for the cron-style agents that relogin every run.) Access JWTs already in flight remain valid until their ~10-min TTL expires; there is no per-JWT revoke for those without a service restart.

### Don't-do list

- Never `export PASSWORD=$(cat ...)` — persists in shell history. Use inline `$(cat ...)` directly inside the JSON body.
- Never send `Authorization: Bearer <anything>` to admin or sot routes — they read the principal from the `portal_access` cookie, not from the header. Bearer headers are silently ignored, so the call falls back to "no auth" and 401s with `missing_access`.
- Never write the password or the cookie jar contents to a tracked path (`docs/`, `_bmad-output/`, anywhere in a git working tree). Cookie jars belong under `/tmp/` or `~/.cache/`, never committed.
- Never mutate without `X-Portal-Client: web` — the CSRF middleware rejects unmarked writes with 403.
- Never re-use an old refresh cookie thinking it's a backup. Refresh-token reuse triggers family invalidation; you'll lose all sessions for the agent user and have to rotate.

## Source Detection

URL host → fetch strategy:

| Host                 | Strategy                                                                                          | Auth needed                                |
| -------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `printables.com`     | GraphQL: list files, then `getDownloadLink` mutation per file (recipe below).                      | None for public models.                    |
| `thangs.com`         | `agent-browser` CLI against the operator's logged-in Windows-host Chrome.                          | Browser session must be logged in already. |
| `thingiverse.com`    | `agent-browser` CLI against the operator's logged-in Windows-host Chrome.                          | Browser session must be logged in already. |
| `makerworld.com`     | `agent-browser` CLI against the operator's logged-in Windows-host Chrome.                          | Browser session must be logged in already. |
| `crealitycloud.com`  | `agent-browser` CLI against the operator's logged-in Windows-host Chrome.                          | Browser session must be logged in already. |

For the four browser-only sources: the `agent-browser` CLI navigates to the model URL, clicks Download, the file lands in `D:\` on the Windows host. Move it into a temporary working directory via PowerShell, then upload via the portal flow. See `~/.claude/CLAUDE.md` § "Browser automation — agent-browser" on the operator's machine for connection setup (mirrored networking, CDP on `localhost:9222`).

New sources are added to this table as a new row; the rest of the runbook does not change.

## Printables GraphQL Recipe

### Endpoint & headers

```
POST https://api.printables.com/graphql/
Content-Type: application/json
```

No authentication is required for public models. The query/mutation signatures below are the form documented in the legacy AGENTS.md and last validated for production use; if you see a GraphQL `errors` array in the response, Printables may have evolved the mutation arguments (e.g. a `files: [{fileType, ids}]` batched shape exists in some clients) — capture the error payload and surface it to the operator rather than guessing a new shape.

### List files (query)

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"{ print(id: \"PRINT_ID\") { stls { id name fileSize } } }"}' \
  https://api.printables.com/graphql/
```

`PRINT_ID` is the numeric ID from the Printables URL (e.g. `https://www.printables.com/model/12345-cali-cat` → `12345`).

Response shape:

```json
{
  "data": {
    "print": {
      "stls": [
        { "id": "STL_ID", "name": "cali_cat.stl", "fileSize": 2048576 }
      ]
    }
  }
}
```

### Get download link (mutation)

For each file `id` returned above:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"mutation { getDownloadLink(id: \"STL_ID\", printId: \"PRINT_ID\", fileType: stl, source: model_detail) { ok output { link } } }"}' \
  https://api.printables.com/graphql/
```

Response shape:

```json
{
  "data": {
    "getDownloadLink": {
      "ok": true,
      "output": { "link": "https://files.printables.com/.../cali_cat.stl?signature=..." }
    }
  }
}
```

### Worked example

For Printables model `661995` (Stanford Bunny — a long-lived public model that is safe to pin as an example):

```bash
# 1) List files
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"{ print(id: \"661995\") { stls { id name fileSize } } }"}' \
  https://api.printables.com/graphql/

# 2) Get download link for one of the returned STL ids
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"mutation { getDownloadLink(id: \"<STL_ID>\", printId: \"661995\", fileType: stl, source: model_detail) { ok output { link } } }"}' \
  https://api.printables.com/graphql/
```

Replace `<STL_ID>` with the value from step 1's response.

### Fetch the file

```bash
curl -L -o /tmp/cali_cat.stl '<link-from-mutation-response>'
```

Use single quotes around the link — the signed URL contains `&` and `?` characters that the shell would otherwise interpret.

## 3MF Conversion (rare-to-near-never path)

Most modern downloads are STL; this path runs only when a `.3mf` file actually arrives in the working directory (URL workflow returning a `.3mf`, manual drop, or ZIP extraction). **No `.3mf` lands in the portal directly** — the catalog only stores per-object STL files derived from each 3MF. If you encounter a `.3mf`, convert before upload.

### How to convert

The conversion script lives in this repo and runs on the **operator's local dev box** (where its `.venv` is installed). Canonical invocation:

```bash
~/repos/3d-portal/infra/scripts/.venv/bin/python \
  ~/repos/3d-portal/infra/scripts/migrate_catalog_3mf.py --convert <path/to/file.3mf>
```

### Post-condition

- Single-object 3MF → one file: `<basename>.stl` in the same directory as the input.
- Multi-object 3MF (≥2 objects) → multiple files: `<basename>_NN.stl`, 1-indexed, zero-padded to at least 2 digits.
- The original `.3mf` is moved to `_archive/3mf-originals/...` next to the working directory.
- Validation: every output STL has > 0 triangles and a non-zero bounding box. Failure leaves the original `.3mf` in place + a flag in the migration report; do not upload anything in that case.

### When you can't run it locally

If you (the agent) are not running on the operator's dev box and cannot invoke the script, do not attempt remote execution. Hand the `.3mf` back to the operator with the note "needs 3MF conversion via `migrate_catalog_3mf.py --convert`". Resume the upload flow once the operator returns the converted STLs.

## Pre-flight Checklist

Verify all five items BEFORE the first portal write call. If any item is false, stop and ask the operator — do not call the model-create endpoint and let the API 4xx absorb the mistake.

1. **Category slug exists.** Fetch the category tree and confirm the target slug is present:
   ```bash
   curl -s -b /tmp/portal-cookies.txt https://3d.ezop.ddns.net/api/categories | jq '.. | objects | .slug? // empty'
   ```
   The portal's `category_id` field on the model-create payload requires a valid UUID; you must pick from the existing tree, not invent a slug.
2. **Model name sanitized.** No Polish diacritics in `name_en`, no leading/trailing whitespace, no file extension. Polish translations belong in `name_pl`.
3. **At least one STL ready to upload.** After any 3MF conversion (above) or OBJ/STEP conversion (use `trimesh.load(path, force='mesh').export(out, file_type='stl')`), the working directory must contain at least one `.stl` file. Verify case-insensitively (some legacy assets are `.STL`): `find . -maxdepth 1 -type f -iname '*.stl'`.
4. **Duplicate check via external links.** The source URL is NOT stored on the model row itself — it lives on a separate `ExternalLink` row attached to the model. Query the existing external-links surface (discover the read endpoint via `/api/openapi.json`) for the source URL; if a match exists, abort the import and return the existing model UUID. The model's `source` field is an enum (`printables`, `thangs`, `unknown`, etc.) and does NOT carry the URL.
5. **No leftover transient files.** No `.3mf`, no `.zip`, no `.7z` in the working directory after extraction + conversion. Only the source files (STL, optional OBJ/STEP keep-original) remain.

## Endpoint Discovery via OpenAPI

For endpoint signatures, request/response schemas, and status codes, fetch `/api/openapi.json` — see e.g. `paths."/api/admin/models".post` and `paths."/api/admin/models/{model_id}/files".post` for the model-create and file-upload surfaces.

To enumerate the full surface without enumerating it here:

```bash
curl -s https://3d.ezop.ddns.net/api/openapi.json | jq '.paths | keys[]'
```

To filter just the endpoints the agent role can WRITE to (model + file + tag + category + note + print + external-link mutations under `/api/admin/...`):

```bash
curl -s https://3d.ezop.ddns.net/api/openapi.json \
  | jq '.paths | to_entries[] | select(.value | .. | objects? | .tags? // [] | index("agent-write")) | .key'
```

Each operation also carries a `summary` (one-liner) + `description` (multi-line, with behavioral side-effects like the auto-render trigger). To see the full enrichment for one endpoint:

```bash
curl -s https://3d.ezop.ddns.net/api/openapi.json \
  | jq '.paths."/api/admin/models".post | {summary, description, tags, requestBody}'
```

The Swagger UI at `https://3d.ezop.ddns.net/api/docs` renders the same surface human-readably; useful for spot-checking but not for programmatic discovery.

## Behavioral Notes

These are behaviors the OpenAPI surface cannot fully express — they affect how you should sequence calls.

- **Auto-render on first STL.** When you upload the first STL file for a model via the multipart file-upload endpoint (`kind=stl` form field, `file` part), the API auto-enqueues a render job in arq. You do not need to call any explicit render endpoint for the initial preview. Subsequent STL uploads do NOT auto-enqueue; trigger render manually if you want a re-render.
- **File deduplication by sha256.** Re-uploading a file with the same content sha256 returns 200 with the existing `ModelFileRead` payload, not 201. Treat 200 here as "already there, OK" — it is not an error.
- **Soft-delete is the norm.** Deleted models keep `deleted_at` set; they vanish from public listings but remain queryable for restore. Hard-delete (`?hard=true`) is admin-only and irreversible.
- **The portal NEVER writes to the Windows catalog.** The legacy `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` folder is read-only from the portal's perspective. Do not attempt to write back there from the portal flow.
- **Auth role gating.** All `/api/admin/*` and `/api/sot/admin/*` write routes require `role=admin` or `role=agent` on the principal cookie. The agent service account has `role=agent`; that is sufficient for model creation, file upload, and the per-model PATCH/DELETE/restore flows. Hard-delete (`?hard=true`) is admin-only — agent role gets a 403 there.

## Putting It Together — Worked Flow

For a Printables URL `https://www.printables.com/model/661995-stanford-bunny`:

1. **Login once.** Run the login `curl` from § "Auth & Login Flow → Login".
2. **Source detection.** Host is `printables.com` → GraphQL recipe.
3. **List files** via the GraphQL query (§ "Printables GraphQL Recipe → List files"). Pick the STL file id(s) you want.
4. **Get download link** for each STL via the mutation. Fetch each link with `curl -L -o`.
5. **3MF conversion?** Inspect the downloaded files; if any is `.3mf`, convert via § "3MF Conversion" before continuing.
6. **Pre-flight checklist.** Walk all 5 items. Fail fast on any false answer.
7. **Pick category.** Fetch `/api/categories`, choose the matching `category_id` UUID.
8. **Create model** via the model-create endpoint (see OpenAPI for the `ModelCreate` body shape; minimum fields are `name_en` + `category_id`; set `source: "printables"`). The response includes the new model UUID. Note: the source URL does NOT belong here.
9. **Attach the source URL** via the external-link create endpoint scoped to the new model UUID (see OpenAPI under the model's `external-links` sub-resource). This is what pre-flight check #4 (duplicate detection) queries on re-imports.
10. **Upload each STL** via the file-upload endpoint scoped to the new model UUID; multipart `file` part + form `kind=stl`. The first STL upload auto-enqueues the render.
11. **Verify.** Fetch the model via the public model-detail endpoint; the `thumbnail` field becomes non-null within ~60 s of the first STL upload as the render completes.

If anything in step 6 fails, stop and ask the operator. If anything in steps 8–11 returns 4xx, read the response body — the API returns descriptive `detail` strings (e.g. `"category not found"`, `"slug already exists"`); fix the input and retry, do not blanket-retry the same payload.
