# 3d-portal — Agent Runbook

This runbook teaches an AI agent (Claude, Codex, or any future LLM) how to add a 3D model to the 3d-portal catalog from a source URL — Printables, Thangs, Thingiverse, MakerWorld, or Creality Cloud. It covers principles, the auth model, source-detection strategy, external-API recipes, the 3MF conversion procedure, the pre-flight checklist, and behavioral side-effects of the portal's API. Endpoint signatures, request/response schemas, and status codes are NOT in this document — they live in the auto-generated OpenAPI surface at `/api/openapi.json`, which pairs with this runbook.

## Principles

- **Pull-only ergonomics.** The portal serves discovery and accepts writes; it never pushes. The agent decides cadence — fetch this runbook + OpenAPI on demand, login once per session, reuse the cookie.
- **REST + cookie session.** All admin/sot calls go over HTTPS to `https://3d.ezop.ddns.net`. Auth is a JWT carried in the `portal_access` cookie set by the login endpoint. There is no long-lived bearer token; do NOT send `Authorization: Bearer ...` headers.
- **Idempotence.** Re-importing the same source URL must not duplicate models. Pre-flight check #4 (duplicate-check) gates this via the `external_url` query parameter on `GET /api/models` — a single call returns the matching `ModelSummary` rows in `.items[]` (empty if not imported). Combine with `include_deleted=true` to also surface soft-deleted prior imports — the agent can then choose between restore-existing vs. fresh-import on hit.
- **Layered auto-discovery.** This runbook documents narrative, behavioral rules, and external-API recipes. The portal's own endpoints, request shapes, and status codes live in `/api/openapi.json` — query that, not source code.

## Auth & Login Flow

### Service account & credentials

The agent service account is a regular `User` row with `role=agent`, provisioned on `.190` (the dev/working portal host on the operator's home LAN, `192.168.2.190`; canonical public URL `https://3d.ezop.ddns.net`) via `python -m scripts.bootstrap_agent --email <agent-email>` (the operator picks the email at first bootstrap). Credentials live on the agent host at `~/.config/3d-portal/agent.token`, mode `600`, owner `ezop`. The file is a JSON credential bundle (NOT a long-lived bearer token):

```json
{
  "email":         "<agent-email>",
  "password":      "<32-char password printed once by bootstrap_agent>",
  "access_token":  "<cached JWT — optional fast-path; may be empty/expired>",
  "expires_at":    "<ISO timestamp for access_token>"
}
```

The `password` is the source of truth — used for fresh login. The `access_token` + `expires_at` pair is an optional cache that lets long-running agents skip the login round-trip if the JWT is still valid; you can ignore both for the simple flow below and just login every session.

### Login (one-time per session)

Extract email + password from the JSON file and POST them to the login endpoint, capturing cookies into a jar:

```bash
em=$(jq -r .email ~/.config/3d-portal/agent.token)
pw=$(jq -r .password ~/.config/3d-portal/agent.token)
curl -s -c /tmp/portal-cookies.txt \
  -X POST \
  -H 'X-Portal-Client: web' \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$em\",\"password\":\"$pw\"}" \
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
em=$(jq -r .email ~/.config/3d-portal/agent.token)
python -m scripts.bootstrap_agent --email "$em" --rotate
```

The script prints the new password to stdout exactly once. Update the JSON file on every host where the agent runs (`chmod 600` preserved). Convenience one-liner:

```bash
new_pw="<paste-from-bootstrap-stdout>"
jq --arg p "$new_pw" '.password = $p | .access_token = "" | .expires_at = ""' \
  ~/.config/3d-portal/agent.token > ~/.config/3d-portal/agent.token.new \
  && mv ~/.config/3d-portal/agent.token.new ~/.config/3d-portal/agent.token \
  && chmod 600 ~/.config/3d-portal/agent.token
```

(The `access_token = ""` + `expires_at = ""` reset clears the cached JWT so the next call performs a fresh login.) No service restart needed.

**Rotation alone is NOT sufficient against a captured cookie.** `--rotate` changes the password hash only; any `portal_refresh` cookie an attacker captured before rotation can still mint new access cookies for the rest of its ~30-day TTL. After every credential compromise, the operator must ALSO revoke all active refresh families for the agent user. The simplest path: relogin with the new password (which gives you a fresh cookie jar), then call the logout-others endpoint to revoke every OTHER family for the same user:

```bash
# 1) Relogin with the new password (overwrites the cookie jar with a fresh access+refresh pair)
em=$(jq -r .email ~/.config/3d-portal/agent.token)
pw=$(jq -r .password ~/.config/3d-portal/agent.token)
curl -s -c /tmp/portal-cookies.txt \
  -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
  -d "{\"email\":\"$em\",\"password\":\"$pw\"}" \
  https://3d.ezop.ddns.net/api/auth/login

# 2) Revoke every OTHER refresh family for this user (keeps the just-logged-in session)
curl -s -b /tmp/portal-cookies.txt -X POST -H 'X-Portal-Client: web' \
  https://3d.ezop.ddns.net/api/auth/logout-others
```

(Use `logout-all` instead of `logout-others` if you want to invalidate the current session too — useful for the cron-style agents that relogin every run.) Access JWTs already in flight remain valid until their ~10-min TTL expires; there is no per-JWT revoke for those without a service restart.

### Don't-do list

- Never `export PASSWORD=$(jq -r .password ...)` — persists in shell history. Use inline `$(jq -r .password ...)` directly inside the JSON body of the login request.
- Never send `Authorization: Bearer <anything>` to admin or sot routes — they read the principal from the `portal_access` cookie, not from the header. Bearer headers are silently ignored, so the call falls back to "no auth" and 401s with `missing_access`. The `access_token` field in `agent.token` is for OPTIONAL agent-side caching of the JWT — it's NOT meant to be sent as a Bearer header to this API.
- Never write the password or the cookie jar contents to a tracked path (`docs/`, `_bmad-output/`, anywhere in a git working tree). Cookie jars belong under `/tmp/` or `~/.cache/`, never committed. The `agent.token` JSON file itself stays at `~/.config/3d-portal/` (mode 600) — never copy it.
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

### Host → `source` enum mapping

`ModelCreate.source` (on the model row) and `ExternalLinkCreate.source` (on the attached external link) are TWO DIFFERENT enums. Use this table when populating either:

| Host                | `ModelSource` (model row) | `ExternalSource` (external link) |
| ------------------- | -------------------------- | --------------------------------- |
| `printables.com`    | `printables`               | `printables`                      |
| `thangs.com`        | `thangs`                   | `thangs`                          |
| `thingiverse.com`   | `thingiverse`              | `thingiverse`                     |
| `makerworld.com`    | `makerworld`               | `makerworld`                      |
| `cults3d.com`       | `cults3d`                  | `cults3d`                         |
| `crealitycloud.com` | `other`                    | `other`                           |
| (no source URL)     | `own` or `unknown`         | n/a (skip external-link step)     |

`ModelSource` has `unknown` (default) + `own` for in-house designs; `ExternalSource` has neither (a link must point at a real source). For `crealitycloud.com` the runbook intentionally maps to `other` until/unless a `crealitycloud` enum value is added on both sides — see `_bmad-output/triage-backlog.md` if you think the enum should be extended.

Always fetch the canonical enum values from OpenAPI before sending (see § "Endpoint Discovery via OpenAPI → Enums") — the source of truth is the API, not this table.

New sources are added to both this table and the host → fetch-strategy table above as a new row; the rest of the runbook does not change.

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
  -d '{"query":"{ print(id: PRINT_ID) { stls { id name fileSize } } }"}' \
  https://api.printables.com/graphql/
```

`PRINT_ID` is the numeric ID from the Printables URL (e.g. `https://www.printables.com/model/12345-cali-cat` → `12345`). Pass it as a bare integer literal in the GraphQL document (no quotes) — Printables types `id`/`printId` as GraphQL `Int`. The double-escaped quoted form (`"\"12345\""`) coerces to GraphQL `String` and the server rejects it with a `data.errors` array.

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

For each file `id` returned above (same Int-not-String rule applies to both arguments):

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"mutation { getDownloadLink(id: STL_ID, printId: PRINT_ID, fileType: stl, source: model_detail) { ok output { link } } }"}' \
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

For Printables model `1000` (Prusa MK3 LED Lamp by Prusa — a long-lived public model uploaded ~2018 with three small STLs, safe to pin as a stable example):

```bash
# 1) List files
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"{ print(id: 1000) { stls { id name fileSize } } }"}' \
  https://api.printables.com/graphql/

# 2) Get download link for one of the returned STL ids (e.g. id 3613, ledtray.stl, ~2 KB)
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"mutation { getDownloadLink(id: 3613, printId: 1000, fileType: stl, source: model_detail) { ok output { link } } }"}' \
  https://api.printables.com/graphql/
```

If a future Printables API change returns a `data.errors` array on this shape, surface the error payload to the operator rather than guessing a new shape — Story 4.5 smoke-test (2026-05-11) verified the integer form works against print 1000.

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
   The portal's `category_id` field on the model-create payload requires a valid UUID; you must pick from the existing tree, not invent a slug. The tree is recursive (`roots[].children[].children[]...`), so map slug → UUID in one shot with `jq`'s `..` recursive descent — works at any depth:
   ```bash
   slug=cats   # the slug you want
   curl -s -b /tmp/portal-cookies.txt https://3d.ezop.ddns.net/api/categories \
     | jq -r --arg s "$slug" '.. | objects | select(.slug? == $s) | .id'
   ```
   Empty stdout = slug not found anywhere in the tree (stop and ask the operator).
2. **Model name sanitized.** No Polish diacritics in `name_en`, no leading/trailing whitespace, no file extension. Polish translations belong in `name_pl`. **How to derive `name_en` per source:**
   - **Printables URL slug** (`/model/<id>-<slug-words>`): strip the leading numeric id and the trailing dash, replace `-` with spaces, title-case. Example: `1000-prusa-mk3-led-lamp` → `Prusa MK3 LED Lamp`. One-liner:
     ```bash
     echo "1000-prusa-mk3-led-lamp" | sed -E 's/^[0-9]+-//; s/-/ /g' \
       | awk '{for(i=1;i<=NF;i++)$i=toupper(substr($i,1,1)) substr($i,2)}1'
     ```
   - **Browser-only sources** (Thangs, Thingiverse, MakerWorld, Creality Cloud): grab the `<title>` of the model page via `agent-browser` (it strips the trailing site brand) and clean similarly.
   - **Sanity-check** the result against the source page's headline before sending. If the slug-derived form looks awkward (acronyms uppercased wrong, brand names mangled), prefer the page title or ask the operator — `name_en` is user-visible and not trivial to rename later (it changes the auto-generated portal slug).
3. **At least one STL ready to upload.** After any 3MF conversion (above) or OBJ/STEP conversion (use `trimesh.load(path, force='mesh').export(out, file_type='stl')`), the working directory must contain at least one `.stl` file. Verify case-insensitively (some legacy assets are `.STL`): `find . -maxdepth 1 -type f -iname '*.stl'`.
4. **Duplicate check via external links.** The source URL is NOT stored on the model row itself — it lives on a separate `ExternalLink` row attached to the model. Use the `external_url` query parameter on `GET /api/models` for a one-shot lookup; a hit returns the existing model row(s), a miss returns `items: []` and `total: 0` so the agent proceeds with a fresh import. The model's `source` field is an enum (`printables`, `thangs`, `unknown`, etc.) and does NOT carry the URL. **Pass `include_deleted=true`** so a previously-imported-then-soft-deleted model is surfaced too — otherwise the dedup check returns 0 and you risk creating a duplicate (or hitting a unique-slug conflict downstream); on hit, inspect the row's `deleted_at` field to decide: restore the existing model vs. proceed with a fresh import.
   ```bash
   curl -s -b /tmp/portal-cookies.txt --get \
     --data-urlencode "external_url=https://www.printables.com/model/1000" \
     --data-urlencode "include_deleted=true" \
     https://3d.ezop.ddns.net/api/models \
     | jq '{total, items: [.items[] | {id, slug, deleted_at}]}'
   ```
   Typically returns 0 or 1 row. URL-encode the source URL via `--data-urlencode` so `?` `&` `#` characters in the URL don't corrupt the query string.
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

Enums (`ModelSource`, `ModelStatus`, `ModelFileKind`, `NoteKind`, `UserRole`) are emitted into `components.schemas`. To dump the canonical `source` values the model-create endpoint accepts:

```bash
curl -s https://3d.ezop.ddns.net/api/openapi.json | jq '.components.schemas.ModelSource.enum'
```

Same shape works for `ModelFileKind`, `ModelStatus`, etc. — always read the enum from OpenAPI rather than hard-coding it from this runbook, since the enum can grow without a runbook update.

## Behavioral Notes

These are behaviors the OpenAPI surface cannot fully express — they affect how you should sequence calls.

- **Auto-render on first STL.** When you upload the first STL file for a model via the multipart file-upload endpoint (`kind=stl` form field, `file` part), the API auto-enqueues a render job in arq. You do not need to call any explicit render endpoint for the initial preview. Subsequent STL uploads do NOT auto-enqueue; trigger render manually via `POST /api/admin/models/{model_id}/render` (returns 202 + `{"status": "queued", "status_key": "..."}`). Body `{"selected_stl_file_ids": []}` lets the worker pick the first STL automatically; pass specific file UUIDs to render a chosen subset:
  ```bash
  curl -s -b /tmp/portal-cookies.txt -c /tmp/portal-cookies.txt \
    -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
    -d '{"selected_stl_file_ids": []}' \
    "https://3d.ezop.ddns.net/api/admin/models/$MODEL_ID/render"
  ```
- **File deduplication by sha256.** Re-uploading a file with the same content sha256 returns 200 with the existing `ModelFileRead` payload, not 201. Treat 200 here as "already there, OK" — it is not an error.
- **Soft-delete is the norm.** Deleted models keep `deleted_at` set; they vanish from public listings but remain queryable for restore. Hard-delete (`?hard=true`) is admin-only and irreversible.
- **The portal NEVER writes to the Windows catalog.** The legacy `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` folder is read-only from the portal's perspective. Do not attempt to write back there from the portal flow.
- **Auth role gating.** All `/api/admin/*` and `/api/sot/admin/*` write routes require `role=admin` or `role=agent` on the principal cookie. The agent service account has `role=agent`; that is sufficient for model creation, file upload, and the per-model PATCH/DELETE/restore flows. Hard-delete (`?hard=true`) is admin-only — agent role gets a 403 there.
- **Import flow does NOT touch tags or photos.** Tag attach (`POST /api/admin/models/{id}/tags`), per-print photos (`POST /api/admin/models/{id}/prints`), gallery image uploads (`kind=image` on the file-upload endpoint) all exist in the OpenAPI surface and the agent role can call them, but the worked flow below intentionally skips them. Rationale: the auto-render produces the catalog thumbnail, so a freshly imported model is visually complete without a hand-curated gallery; tagging is operator-driven so far (no source-side metadata mapped automatically). Add tags/photos on operator request, not by default.

## Putting It Together — Worked Flow

For a Printables URL `https://www.printables.com/model/1000-prusa-mk3-led-lamp`:

1. **Login once.** Run the login `curl` from § "Auth & Login Flow → Login".
2. **Source detection.** Host is `printables.com` → GraphQL recipe.
3. **List files** via the GraphQL query (§ "Printables GraphQL Recipe → List files"). Pick the STL file id(s) you want.
4. **Get download link** for each STL via the mutation. Fetch each link with `curl -L -o`.
5. **3MF conversion?** Inspect the downloaded files; if any is `.3mf`, convert via § "3MF Conversion" before continuing.
6. **Pre-flight checklist.** Walk all 5 items. Fail fast on any false answer.
7. **Pick category.** Use the slug → UUID `jq` recipe from § "Pre-flight Checklist → 1. Category slug exists" against `/api/categories` to resolve `CATEGORY_ID`.
8. **Create model** via `POST /api/admin/models` (body: `ModelCreate`; minimum fields are `name_en` + `category_id`; default `source` is `unknown`, so set it explicitly per the host → enum mapping table). The response is a `ModelDetail` row whose `id` is the new model UUID. Note: the source URL does NOT belong on this payload.
   ```bash
   CATEGORY_ID=<uuid-from-step-7>
   MODEL_ID=$(
     curl -s -b /tmp/portal-cookies.txt -c /tmp/portal-cookies.txt \
       -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
       -d "{\"name_en\":\"Prusa MK3 LED Lamp\",\"category_id\":\"$CATEGORY_ID\",\"source\":\"printables\"}" \
       https://3d.ezop.ddns.net/api/admin/models \
     | jq -r .id
   )
   echo "$MODEL_ID"
   ```
   On 4xx, `MODEL_ID` will be `null` — re-run without the `jq -r .id` pipe to read the error body.
9. **Attach the source URL** via `POST /api/admin/models/{model_id}/external-links` (body: `ExternalLinkCreate`; `source` uses the `ExternalSource` enum — see the host mapping table for the value to send). 409 here means a link for that source already exists on this model (one link per source per model is the unique constraint). This is what pre-flight check #4 (duplicate detection) queries on re-imports.
   ```bash
   curl -s -b /tmp/portal-cookies.txt -c /tmp/portal-cookies.txt \
     -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
     -d '{"source":"printables","external_id":"1000","url":"https://www.printables.com/model/1000-prusa-mk3-led-lamp"}' \
     "https://3d.ezop.ddns.net/api/admin/models/$MODEL_ID/external-links"
   ```
10. **Upload each STL** via the file-upload endpoint scoped to the new model UUID; multipart `file` part + form `kind=stl`. The first STL upload auto-enqueues the render. (`$MODEL_ID` is the variable set in step 8.)
    ```bash
    curl -s -b /tmp/portal-cookies.txt -c /tmp/portal-cookies.txt \
      -X POST -H 'X-Portal-Client: web' \
      -F 'file=@/tmp/cali_cat.stl' \
      -F 'kind=stl' \
      "https://3d.ezop.ddns.net/api/admin/models/$MODEL_ID/files"
    ```
    Curl auto-sets the `multipart/form-data` content type from `-F`; do NOT add `-H 'Content-Type: ...'` manually or it will clobber the boundary. Other valid `kind` values: `image`, `print`, `source`, `archive_3mf` (see `ModelFileKind` in OpenAPI).
11. **Verify.** Fetch the model via the public model-detail endpoint (`GET /api/models/{model_id}`, unauthenticated). The `thumbnail_file_id` field flips from `null` to a UUID within ~60 s of the first STL upload as the render completes. Concrete poll loop (12 attempts × 5 s = 60 s budget):
    ```bash
    for i in $(seq 1 12); do
      tid=$(curl -s "https://3d.ezop.ddns.net/api/models/$MODEL_ID" | jq -r '.thumbnail_file_id // empty')
      if [ -n "$tid" ]; then echo "render done after ${i}x5s: $tid"; break; fi
      sleep 5
    done
    [ -z "$tid" ] && echo "render did not land in 60s — check workers/render logs on .190" >&2
    ```
    If the loop times out, the worker log on `.190` (`docker compose logs render --tail 200`) is the next stop — the most common causes are (a) arq pool not connected to redis, (b) the selected STL has zero triangles, (c) the worker container OOM-killed by Docker.

If anything in step 6 fails, stop and ask the operator. If anything in steps 8–11 returns 4xx, read the response body — the API returns descriptive `detail` strings (e.g. `"category not found"`, `"slug already exists"`); fix the input and retry, do not blanket-retry the same payload.
