# Story 4.5 — Agent Runbook Smoke-Test Transcript

**Date:** 2026-05-11
**Executor:** Claude Opus 4.7 (1M context), via BMAD `bmad-dev-story` (autonomous mode)
**Result:** ✅ End-to-end success. One critical runbook gap (auth file format) + four cosmetic gaps surfaced — see § "Runbook gaps".
**Artefact location:** `_bmad-output/implementation-artifacts/agent-runbook-smoke-2026-05-11.md` (gitignored per `feedback_local_only_docs.md`; lives only on operator's dev box).

---

## Smoke-test self-verification (AC §c)

| Check | Method | Result |
|---|---|---|
| (a) `/agent-runbook` returns valid markdown ≥ threshold + intro-paragraph fingerprint matches | `curl /agent-runbook \| wc -l` + awk-extract intro \| sha256sum vs `infra/.runbook-fingerprint` | ✅ 295 lines; sha256 `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` matches baseline |
| (b) `/api/openapi.json` returns valid OpenAPI 3.x with the model-create + file-upload paths defined | `curl /api/openapi.json \| jq '.paths \| keys'` + spot-check `paths."/api/admin/models".post` exists | ✅ 43 paths; both `paths."/api/admin/models".post` and `paths."/api/admin/models/{model_id}/files".post` present |
| (c) `POST /api/admin/models` returned 201 + UUID; `POST /api/admin/models/{id}/files` (multipart STL) returned 201; thumbnail field flipped non-null within 60 s | curl chain + 10 s poll loop | ✅ Model UUID `aa42befe-9e93-4613-99f7-c3c40232bcca`; STL file UUID `6697fc4a-6e5e-4cf8-8c5a-4cfa45b19d4f` (2284 bytes); auto-render landed within first 10 s poll (thumbnail_file_id `47c638cd-da24-45bc-a39b-6b4353d368b8`); final `file_count=5` (1 STL + 4 render outputs) |
| (d) Model is visible on the catalog page | `curl /api/models?q=Smoke+Test` returns the row + thumbnail_file_id | ✅ One match returned with the correct `name_en` + non-null `thumbnail_file_id` |

## NFR8 drift check (AC § "And NFR8")

```bash
curl -fsS https://3d.ezop.ddns.net/agent-runbook \
  | grep -nE '(GET|POST|PUT|PATCH|DELETE) /api/' \
  | grep -v '`'
# → 0 lines (every HTTP-method + /api/ mention is inside backticks per the
#   strict NFR8 reading enforced after Story 4.1 fix-up commit ec27222)
```

✅ Zero violations.

---

## Source URL + smoke-test target choice

- **Operator's prod portal:** `https://3d.ezop.ddns.net`
- **Bootstrap inputs given to the agent (this me, simulating fresh-session):** (1) the portal URL, (2) "fetch `/agent-runbook` for principles + `/api/openapi.json` for endpoints", (3) credentials at `~/.config/3d-portal/agent.password` per the runbook (NOTE: this file does not exist on the operator's box; see § "Runbook gaps" R-1).
- **Printables URL chosen:** `https://www.printables.com/model/1000-prusa-mk3-led-lamp` ("Prusa MK3 LED Lamp" by Prusa). Picked after the runbook's example pin `661995` turned out to be a different model (firearm accessory) — see § "Runbook gaps" R-3. Model 1000 is the smallest plausible neutral 3D-printer accessory, with a 2 KB STL (`ledtray.stl`, file ID `3613`) — fast upload, easy to delete after, fits operator's catalog domain.
- **Target catalog category:** `accessories` slug (UUID `23b779d8-e21e-4d3f-9b05-f619e4bf4c1a`).

---

## Step-by-step transcript

Token / cookie / signed-link values redacted. Commands shown verbatim; output excerpted to the load-bearing fields.

### Step 1 — Bootstrap: fetch `/agent-runbook`

```bash
curl -fsS https://3d.ezop.ddns.net/agent-runbook | wc -l   # → 295
curl -fsS https://3d.ezop.ddns.net/agent-runbook \
  | awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' \
  | sha256sum | awk '{print $1}'
# → 49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573
```

Matches `infra/.runbook-fingerprint` baseline. Self-verify (a) ✓.

### Step 2 — Bootstrap: fetch `/api/openapi.json`

```bash
curl -fsS https://3d.ezop.ddns.net/api/openapi.json | jq '.paths | keys | length'   # → 43
```

Self-verify (b) intermediate. (Continued in Step 13 with the spot-checks for the specific paths.)

### Step 3 — Auth attempt 1: strict runbook

```bash
pw=$(cat ~/.config/3d-portal/agent.password)
# → cat: ~/.config/3d-portal/agent.password: No such file or directory  (exit 1)
```

❌ Failed. The runbook (Story 4.1) instructs reading from `agent.password`, but the operator's actual file is at `~/.config/3d-portal/agent.token` (see § "Runbook gaps" R-1).

### Step 4 — Auth attempt 2: adapt to operator's actual JSON file

Inspected the actual file (without echoing values):

```bash
jq -r 'keys' ~/.config/3d-portal/agent.token
# → ["access_token", "email", "expires_at", "password"]
```

The file is a JSON credential bundle: `{access_token, email, expires_at, password}` — operator caches a JWT alongside the password to avoid re-login per session. Adapted:

```bash
pw=$(jq -r .password ~/.config/3d-portal/agent.token)
em=$(jq -r .email ~/.config/3d-portal/agent.token)
# em → agent@portal.example.com  (note: NOT agent@portal.local from the runbook example)
# pw → 32-char string (redacted)
```

### Step 5 — POST `/api/auth/login`

```bash
curl -s -c cookies.txt -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
  -d "{\"email\":\"$em\",\"password\":\"$pw\"}" \
  https://3d.ezop.ddns.net/api/auth/login
# → {"user":{"email":"agent@portal.example.com","role":"agent",...}}
```

Cookies acquired in `cookies.txt`: `portal_access` (Path=/api, ~10 min TTL) + `portal_refresh` (Path=/api/auth, 30-day TTL). All subsequent calls reuse via `-b cookies.txt`.

### Step 6 — Pre-flight #1: category slug exists

```bash
curl -fsS -b cookies.txt https://3d.ezop.ddns.net/api/categories \
  | jq '[.. | objects | .slug? // empty] | unique | .[:20]'
# → ["accessories", "articulated-figures", "bathroom", "bin-shells", ...]
```

`accessories` slug present. Picked it for the target category.

```bash
CAT_ID=$(curl -fsS -b cookies.txt https://3d.ezop.ddns.net/api/categories \
  | jq -r '.. | objects | select(.slug? == "accessories") | .id' | head -1)
# CAT_ID → 23b779d8-e21e-4d3f-9b05-f619e4bf4c1a
```

### Step 7 — Pre-flight #4: dedup check (no model already linked to this Printables URL)

```bash
curl -fsS -b cookies.txt 'https://3d.ezop.ddns.net/api/models?q=stanford+bunny&limit=5' \
  | jq '.items | length'
# → 0
```

Zero hits (and the chosen URL `printables.com/model/1000` is also unique — see § "Runbook gaps" R-4 for why I changed targets mid-flow).

### Step 8 — Source detection: `printables.com` → GraphQL recipe

Per runbook source-detection table.

### Step 9 — Printables GraphQL: list STL files for print 1000

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"{ print(id: 1000) { stls { id name fileSize } } }"}' \
  https://api.printables.com/graphql/
# →
# {
#   "data": { "print": { "stls": [
#     {"id":"3614","name":"ledleftarm.stl","fileSize":9884},
#     {"id":"3613","name":"ledtray.stl","fileSize":2284},
#     {"id":"3615","name":"ledrightarm.stl","fileSize":9884}
#   ]}}
# }
```

Picked file ID `3613` (`ledtray.stl`, 2.3 KB — smallest, fastest for the smoke test).

### Step 10 — Printables GraphQL: get download link

```bash
LINK=$(curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"mutation { getDownloadLink(id: 3613, printId: 1000, fileType: stl, source: model_detail) { ok output { link } } }"}' \
  https://api.printables.com/graphql/ \
  | jq -r '.data.getDownloadLink.output.link')
# LINK length: 105 chars (signed URL — full value redacted)
```

The legacy mutation signature (`id`, `printId`, `fileType`, `source` as top-level args) **works as documented in the runbook**. Codex's Story-4.1 P2-deferred concern about the API having evolved to a `files: [{fileType, ids}]` shape did NOT materialize — Printables still accepts the legacy form against print id 1000. (Validated 2026-05-11; could change without notice on Printables' side.)

### Step 11 — Fetch the STL

```bash
curl -L -fsS -o /tmp/smoke-4.5/ledtray.stl "$LINK"
ls -la /tmp/smoke-4.5/ledtray.stl
# → -rw-r--r-- 1 ezop ezop 2284 May 11 02:21 ledtray.stl
```

### Step 12 — Pre-flight checklist (full sweep)

| # | Check | Result |
|---|---|---|
| 1 | Category slug exists | ✅ `accessories` UUID `23b779d8-...` |
| 2 | Name sanitized | ✅ `Smoke Test - Prusa MK3 LED Lamp (E4.5)` — ASCII hyphen + parens; no Polish diacritics; no leading/trailing whitespace; no extension |
| 3 | At least one STL ready | ✅ `find . -maxdepth 1 -type f -iname '*.stl' \| wc -l` → 1 |
| 4 | Dedup | ✅ 0 hits for "stanford bunny" search; new Printables URL also unique |
| 5 | No transient files | ✅ `find . -maxdepth 1 -type f \( -iname '*.3mf' -o -iname '*.zip' -o -iname '*.7z' \)` → 0 |

### Step 13 — Create model

```bash
curl -s -b cookies.txt -c cookies.txt -X POST \
  -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
  -d "{\"name_en\":\"Smoke Test - Prusa MK3 LED Lamp (E4.5)\", \
       \"name_pl\":\"Smoke Test - Prusa MK3 lampka (E4.5)\", \
       \"category_id\":\"$CAT_ID\", \
       \"source\":\"printables\", \
       \"status\":\"not_printed\"}" \
  https://3d.ezop.ddns.net/api/admin/models
# → {"id":"aa42befe-9e93-4613-99f7-c3c40232bcca", "name_en":"Smoke Test - Prusa MK3 LED Lamp (E4.5)", ...}
MODEL_ID=aa42befe-9e93-4613-99f7-c3c40232bcca
```

201 Created. Self-verify (b) confirmed: `paths."/api/admin/models".post` is real.

### Step 14 — Attach Printables URL via external-link

```bash
curl -s -b cookies.txt -c cookies.txt -X POST \
  -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
  -d '{"source":"printables", "external_id":"1000", "url":"https://www.printables.com/model/1000-prusa-mk3-led-lamp"}' \
  "https://3d.ezop.ddns.net/api/admin/models/$MODEL_ID/external-links"
# → {"url":"https://www.printables.com/model/1000-prusa-mk3-led-lamp", "external_id":"1000", ...}
```

201 Created. (Story 4.1 fix-up corrected the runbook to use this two-step model-create + external-link flow rather than the originally-proposed `source_url` field on `ModelCreate` — which doesn't exist.)

### Step 15 — Upload STL (multipart)

```bash
curl -s -b cookies.txt -c cookies.txt -X POST -H 'X-Portal-Client: web' \
  -F "file=@/tmp/smoke-4.5/ledtray.stl" -F "kind=stl" \
  "https://3d.ezop.ddns.net/api/admin/models/$MODEL_ID/files"
# → {"id":"6697fc4a-6e5e-4cf8-8c5a-4cfa45b19d4f", "original_name":"ledtray.stl", "kind":"stl", "size_bytes":2284, ...}
```

201 Created. Self-verify (b) confirmed: `paths."/api/admin/models/{model_id}/files".post` is real.

### Step 16 — Verify auto-render (poll thumbnail field for up to 60 s)

```bash
for i in 1 2 3 4 5 6; do
  sleep 10
  curl -s -b cookies.txt "https://3d.ezop.ddns.net/api/models/$MODEL_ID" | jq -r '.thumbnail_file_id // "null"'
done
# poll 1 (after 10s): thumbnail_file_id=47c638cd-da24-45bc-a39b-6b4353d368b8
```

✅ Auto-render landed within the **first 10 s** poll. The `model_has_auto_renders` gate (per Story 4.3 description fix-up) was correctly empty at upload time, the arq-worker rendered the STL, and the model now has a thumbnail. Self-verify (c) ✓.

### Step 17 — Final catalog visibility

```bash
curl -s -b cookies.txt "https://3d.ezop.ddns.net/api/models?q=Smoke+Test&limit=5" \
  | jq '.items | map({id, name_en, thumbnail_file_id})'
# → [
#     {"id":"aa42befe-...", "name_en":"Smoke Test - Prusa MK3 LED Lamp (E4.5)",
#      "thumbnail_file_id":"47c638cd-..."}
#   ]
```

Model is visible in the public catalog list with a non-null thumbnail. Self-verify (d) ✓.

```bash
curl -s -b cookies.txt "https://3d.ezop.ddns.net/api/models/$MODEL_ID" \
  | jq '{id, name_en, source, status, thumbnail_file_id, file_count: (.files | length)}'
# → {
#     "id":"aa42befe-...", "name_en":"Smoke Test - Prusa MK3 LED Lamp (E4.5)",
#     "source":"printables", "status":"not_printed",
#     "thumbnail_file_id":"47c638cd-...",
#     "file_count": 5
#   }
```

`file_count: 5` = 1 uploaded STL + 4 render-output files (front/side/top/iso renders, the worker's standard quartet). Confirms the auto-render path completed end-to-end.

---

## Runbook gaps (feed Story 4.6 OR follow-up runbook edits)

These are friction points an actual fresh-session AI agent would hit when following the runbook as-written today. Severity is from "would-block-the-flow" (R-1) down to "cosmetic readability" (R-5).

### R-1 [P1] — Auth file format mismatch (BLOCKER for strict runbook follow)

**Runbook says:** read raw password from `~/.config/3d-portal/agent.password`.
**Operator's actual setup:** JSON credential bundle at `~/.config/3d-portal/agent.token` with keys `{access_token, email, expires_at, password}` (the operator caches a JWT alongside the password to avoid re-login per session).

**Effect on a fresh agent:** strict-runbook follow would `cat agent.password` → `No such file or directory` (exit 1) and stop. Without inspection, the agent has no way to discover the actual file path or shape.

**Two ways to close this gap — operator's call:**

- **Path A (update runbook to match operator config):** rewrite the runbook auth section to: read JSON from `~/.config/3d-portal/agent.token`, extract `password` via `jq -r .password`, optionally use `access_token` + `expires_at` for the JWT-cache fast path (skip login if not expired). Pro: matches what the operator already has; agents adopt the existing optimization. Con: introduces a `jq` dependency in the auth boilerplate (every AI-agent host needs `jq` installed; arguably standard for shell-driven agents anyway).
- **Path B (rename/restructure operator config to match runbook):** create `~/.config/3d-portal/agent.password` containing just the 32-char password; keep the JSON cache as a separate optimization file (e.g. `agent.token-cache`). Pro: keeps the runbook simple (no `jq`); agents follow it literally. Con: operator has to update all his existing agent-driven scripts to read from the new file.

**Recommendation:** Path A. The operator's caching pattern is genuinely useful (avoids a login round-trip per session), and documenting it in the runbook makes it the canonical AI-agent pattern rather than private operator tooling. Cost is one runbook edit + a cohort of `jq` snippets in the auth examples.

### R-2 [P2] — Email mismatch in runbook examples

**Runbook example uses:** `agent@portal.local`.
**Operator's actual address:** `agent@portal.example.com`.

**Effect on a fresh agent:** if the agent copies the example email literally instead of reading `email` from the credential file, login fails with `invalid_credentials`. Workaround is trivial (read the file), but the runbook example primes the wrong default.

**Fix:** in the runbook auth section, replace the literal `"email":"agent@portal.local"` with a `read-from-file` pattern (paired with the R-1 fix), e.g. `"email":"$(jq -r .email ~/.config/3d-portal/agent.token)"`. No more hardcoded example address.

### R-3 [P2] — Worked-example Printables ID is wrong

**Runbook says:** "For Printables model `661995` (Stanford Bunny — a long-lived public model that is safe to pin as an example)".
**Reality (verified 2026-05-11):** Printables 661995 is a **firearm accessory** (SFAv2 Quad 12GA Clip parts, file names `SFAv2 Quad 12GA Clip 1 20.2.STL` etc.), NOT Stanford Bunny.

**Effect on a fresh agent:** if the agent uses the example literally and the operator's catalog domain doesn't include shooting-sports gear, the model creation lands with semantically-wrong content. Smoke-test caught this and pivoted to Printables 1000 (Prusa MK3 LED Lamp — properly neutral) for the actual upload.

**Fix:** swap the worked-example ID. Printables 1000 (Prusa MK3 LED Lamp) is genuinely long-lived (uploaded ~2018), small (3 STLs, ~10 KB total), neutral, and topical for a 3D-printing portal. Substitute it for 661995 in the runbook's "Worked example" subsection.

### R-4 [P3] — Pre-flight #4 dedup check is described in narrative but no concrete query example

**Runbook says** (post-Story-4.1-fix-up): "Query the existing external-links surface (discover the read endpoint via `/api/openapi.json`) for the source URL".
**Practical friction:** a fresh agent has to discover the read-side external-links endpoint via OpenAPI introspection. The current SoT public-read router (`/api/...`) does NOT expose a "list models by external-link URL" endpoint — agents end up doing `GET /api/models?q=<keywords>` (text search on names) and hoping for the best, OR fetching every model's detail and grepping. Neither is great UX.

**Fix:** either (a) add a query-param `external_url=<url>` to `GET /api/models` that filters on the external-links join (small API addition; one-line story), OR (b) make the runbook acknowledge the limitation and recommend "after model creation, attach the external-link; if the API rejects with `source_conflict` it means a model is already linked to that source URL — query OpenAPI for the conflict-detection endpoint or re-search". Option (a) is cleaner.

### R-5 [P3] — `jq` snippet in OpenAPI Discovery section has a slice-syntax bug

**Runbook says:** `curl -s https://3d.ezop.ddns.net/api/openapi.json | jq '.paths | keys[]'` (this works) — but my earlier verification while running this smoke-test typed `jq '.paths | keys | length, (keys | .[:5])'` which returned `[0,1,2,3,4]` (numeric indices, not the path strings). The runbook's snippet is correct; this is operator-side noise — but worth noting in case future runbook examples show slice patterns, they should use `[.paths | keys][0:5]` for safety.

**Fix:** none required for the runbook itself; flagged as a self-note for future runbook expansions.

---

## Cleanup

The smoke-test created one real catalog row that lives indefinitely in the prod portal:

- Model UUID: `aa42befe-9e93-4613-99f7-c3c40232bcca`
- Name: `Smoke Test - Prusa MK3 LED Lamp (E4.5)`
- Slug: auto-generated; visible at `https://3d.ezop.ddns.net/` filtered by `q=Smoke+Test`
- File: 1 STL (`ledtray.stl`, 2.3 KB) + 4 render outputs (auto-generated)

**To delete after operator review:**

```bash
pw=$(jq -r .password ~/.config/3d-portal/agent.token)
em=$(jq -r .email ~/.config/3d-portal/agent.token)
curl -s -c /tmp/cookies.txt -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
  -d "{\"email\":\"$em\",\"password\":\"$pw\"}" \
  https://3d.ezop.ddns.net/api/auth/login >/dev/null
curl -s -b /tmp/cookies.txt -X DELETE -H 'X-Portal-Client: web' \
  "https://3d.ezop.ddns.net/api/admin/models/aa42befe-9e93-4613-99f7-c3c40232bcca"
# → soft-delete (returns ModelDetail with deleted_at set; row is restorable)
```

Or hard-delete via `?hard=true` (admin role required; agent role gets 403 here per Story 4.3 description).

Local test workspace `/tmp/smoke-4.5/` (cookies.txt + ledtray.stl + model_id.txt) — cleanup with `rm -rf /tmp/smoke-4.5`.

---

## NFR-by-NFR coverage

| NFR | Status |
|---|---|
| NFR1 (pull-only ergonomics) | ✓ Entire flow is `curl` against REST, no push, no webhooks |
| NFR2 (credentials-at-rest scope) | ⚠ Operator's `agent.token` JSON file is mode 600 + owner ezop (verified earlier) — caching `access_token` in the JSON does mean a stolen file leaks BOTH the password AND a long-lived JWT. Within homelab single-tenant scope this is acceptable; flag if the threat model widens |
| NFR3 (verification before completion) | ✓ This transcript IS the verification artifact |
| NFR4 (decision documentation) | ✓ N/A for this story (no irreversible action; Story 4.4 covers the decision-doc surface) |
| NFR5 (agent-portable: Claude AND Codex executable) | ⚠ This run was Claude-only. Cross-LLM execution by Codex is OUT of scope for this transcript; recommend Codex re-run as a follow-up sanity check after R-1 / R-3 runbook fixes land |
| NFR6 (idempotent URL re-import) | ⚠ Not exercised — would require running the flow twice with the same Printables URL and verifying the second run returns the existing UUID rather than creating a duplicate. R-4 (dedup-by-URL endpoint missing) is the precondition |
| NFR7 (deploy verify includes runbook endpoint) | ✓ `infra/scripts/deploy.sh` runbook fingerprint check is wired (Story 4.2); both deploys today (commits 9ac52f6 + 565b347) emitted `✓ runbook fingerprint OK` |
| NFR8 (auto-discovery — no signature duplication) | ✓ Runbook has 0 non-backticked `METHOD /api/...` mentions (grep heuristic above) |

---

## Recommendations to operator

In priority order:

1. **R-1 — adopt Path A** (update runbook to match the JSON credential-file pattern). One commit to `docs/agents-add-model-runbook.md` + fingerprint update if the intro paragraph changes (it shouldn't — only the auth section changes).
2. **R-3 — swap the Printables example** from 661995 to 1000 in the same runbook commit.
3. **R-2 — replace the literal email** with a `jq -r .email ...` read pattern in the same runbook commit.
4. **R-4 — small story to add `external_url=<url>` filter to `GET /api/models`** (proper dedup primitive). Or accept the OpenAPI-discovery + try-and-handle-409 pattern as the documented workaround.
5. **NFR6 — second smoke-test run** after R-1/R-3 land, to exercise the idempotence path (re-import same URL → existing UUID, no duplicate).
6. **NFR5 — Codex cross-LLM smoke-test** as the final acceptance (the agent runbook should work end-to-end for an LLM that wasn't involved in writing it).
7. **Clean up the test model** when ready (`DELETE /api/admin/models/aa42befe-...` per the cleanup snippet).

The runbook surface is structurally sound — bootstrap → auth → source-detection → flow all worked end-to-end. The gaps are content/example accuracy, not architectural.
