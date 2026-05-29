# Phase 0 Dry-Run Gate Result

- **Date:** 2026-05-09T02:30Z (UTC, approximate)
- **Operator:** autonomous AI agent (Claude Opus 4.7, 1M context) — running while Michał asleep
- **Plugin version tested:** `@sentry/vite-plugin@~5.2.0` (resolved: **5.2.1**)
- **GlitchTip endpoint configured in plugin (`url`):** `http://192.168.2.190:8800`
- **Release tag used:** `0.1.0+phase0`
- **Local Node:** v24.6.0 (via `nvm use default`); Dockerfile baseline is `node:22-alpine` — both well past `import.meta.dirname` cutoff (Node 20.11+) required by `unplugin` (transitive dep of `@sentry/vite-plugin`).

## Outcome

- [ ] **happy-path** — chunk upload 200, assemble 200, files endpoint listed N artifacts. Stories 1.4 and 1.5 PROCEED.
- [ ] **fallback-path** — `assemble` returned 404 (issue #299 fired). Stories 1.4 and 1.5 CLOSE as won't-ship; CLI flow remains active path.
- [x] **THIRD CATEGORY — plugin-blocked, server-config remediable** — chunk upload returned **HTTP 413 (Payload Too Large)** at the chunk upload step (BEFORE `assemble` was reached, so issue #299 was NOT triggered). Operator decision required to proceed; see "Decision required" section below.

## Build log excerpt

The plugin completed `vite build` successfully (`✓ built in 6.84s`); the failure was post-build at the source-map upload step:

```
> Bundled 8 files for upload
> Bundle ID: af73a9e4-d291-59f7-b8ed-8d8a26762d1a
> Optimizing completed in 0.004s
error: API request failed

Caused by:
    sentry reported an error: unknown error (http status: 413)

[sentry-vite-plugin] Error: An error occurred. Couldn't finish all operations:
Error: Command sourcemaps upload -p 3d-portal --release 0.1.0+phase0
  /tmp/sentry-bundler-plugin-upload-jTT9Ze --ignore node_modules --no-rewrite
  failed with exit code 1
✓ built in 6.84s
```

Source-map sizes built locally:

| File | Map size |
|---|---|
| `dist/assets/index-rk0eKowK.js.map` | **3,908 kB** (~3.9 MB) |
| `dist/assets/measureReducer-B2W5fEzt.js.map` | **3,709 kB** (~3.7 MB) |
| `dist/assets/Viewer3DModal-CGEjyp-0.js.map` | 32 kB |
| `dist/assets/Viewer3DInline-BGYWS-57.js.map` | 21 kB |

The two large maps drive the 413.

## Root cause analysis

The plugin's chunk-upload protocol works like this:

1. **GET** `<url>/api/0/organizations/<org>/chunk-upload/` — fetch chunk-upload server config.
2. **POST** chunks to the URL returned in the config response.

The plugin was configured with `url: 'http://192.168.2.190:8800'` (LAN). Step 1 hit `:8800` and got HTTP 200 with this body:

```json
{
  "url": "https://glitchtip.ezop.ddns.net/api/0/organizations/homelab/chunk-upload",
  "chunkSize": 33554432,
  "chunksPerRequest": 1,
  "maxFileSize": 2147483648,
  "maxRequestSize": 33554432,
  "concurrency": 1,
  "hashAlgorithm": "sha1",
  "compression": ["gzip"],
  "accept": ["debug_files", "release_files", "pdbs", "sources", "artifact_bundles", "proguard"]
}
```

**The server returned `https://glitchtip.ezop.ddns.net/...` as the upload URL** — the public HTTPS proxy. Step 2 sent multi-MB chunks to that URL, and the public proxy (nginx in `~/repos/configs/nginx/3d-portal.conf` or equivalent) capped the body at 1 MB → HTTP 413.

The architecture's "LAN bypass" via the plugin's `url` option only covers Step 1 (config fetch). Step 2 honors the server-returned URL — the plugin has no way to override it, and the architecture's ":8800 bypass" assumption is incomplete on this specific GlitchTip configuration.

## Direct sentry-cli with `--url` LAN: works

To prove the LAN endpoint itself accepts large bodies, I ran (inside the worktree, immediately after the plugin failure):

```bash
./node_modules/.bin/sentry-cli \
  --url http://192.168.2.190:8800 \
  --auth-token "$SENTRY_AUTH_TOKEN" \
  sourcemaps upload \
  --org homelab --project 3d-portal \
  --release 0.1.0+phase0-direct --no-rewrite \
  dist/assets
```

Result:

```
> Bundled 6 files for upload
> Bundle ID: bc0088d1-ac7d-50d5-85d4-cfb0c7d273ea
> Uploading completed in 0.318s
> Uploaded files to Sentry
> File upload complete (processing pending on server)
> Upload type: artifact bundle
```

**HTTP 200 throughout.** The LAN URL works fine for direct sentry-cli; the plugin couldn't use it because GlitchTip server-side returned the public URL. The CLI's `--url` flag is honored end-to-end (config fetch + chunk upload).

This means the existing `infra/scripts/upload-sourcemaps.sh` (CLI flow, baseline 2026-04-30) is **not subject to this issue**. The CLI fallback path remains fully functional.

(Note: `0.1.0+phase0-direct` does NOT appear under `releases/` because modern `sentry-cli sourcemaps upload` uses **debug-IDs + artifact bundles** — no per-release file association is created. The bundle is uploaded and looked up by debug-ID at symbolication time. This is the modern flow and works the same way for the production CLI script.)

## Issue #299 status: NOT triggered (different failure mode)

The architecture's Phase 0 gate was designed to detect issue [#299](https://github.com/glitchtip/glitchtip-backend/issues/299) where `artifactbundle/assemble` returns 404. The current failure happened **upstream** of `assemble` (at the chunk-upload step itself, HTTP 413). The `assemble` endpoint was never reached. Issue #299 cannot be evaluated against this homelab instance until the chunk-upload phase completes.

## Decision required (operator)

Three paths forward; operator picks one. **Sprint-status updates and `epics.md` Phase 0 branching note are deferred until this decision is made.** Stories 1.2, 1.3, 1.6, all of E2 (2.1–2.5), and all of E3 (3.1–3.4) remain valid regardless of the choice — only stories 1.4 and 1.5 are gated.

### Option A — Fix GlitchTip server config (recommended path-of-least-regret)

Make GlitchTip return the LAN URL on the chunk-upload config endpoint when accessed from LAN. Likely mechanisms (operator should investigate; architecture didn't cover this):

- Look for `GLITCHTIP_DOMAIN` / `GLITCHTIP_URL` / `SENTRY_URL` env var on the GlitchTip container in `infra/docker-compose.yml` on `.190`.
- Check whether the container is configured with a public-only `GLITCHTIP_DOMAIN=https://glitchtip.ezop.ddns.net` and whether removing/adjusting it would let GlitchTip default to using the request `Host` header (which would be `192.168.2.190:8800` for LAN traffic).
- Consider adding `proxy_set_header Host $host;` and similar in any `:8800`-fronting nginx/edge if GlitchTip honors `X-Forwarded-Host`.

After the config change, re-run Phase 0 (`bash infra/scripts/upload-sourcemaps.sh` against current build is a good proxy test before re-running the full plugin dry-run). Then if Phase 0 returns happy-path, proceed with Stories 1.4 and 1.5.

**Effort:** likely <1h investigation + 1 docker-compose redeploy + 1 Phase 0 re-run. **Risk:** GlitchTip might genuinely need the public URL for the SDK envelope endpoint; care needed to not break runtime ingestion.

### Option B — Increase nginx body limit on the public proxy

If the public proxy is something Michał controls (likely in `~/repos/configs/nginx/`), bump `client_max_body_size` to e.g., 50 MB on the chunk-upload path. Lets the plugin upload via the public URL.

**Effort:** ~5 min config change + nginx reload (via `~/repos/configs/sync.sh`). **Risk:** larger attack surface for body-size DoS on the public endpoint; likely acceptable for a homelab instance behind authentication.

### Option C — Accept fallback-path (close E1 1.4 and 1.5 as won't-ship)

The CLI flow already works against this exact GlitchTip — proven by the existing `infra/scripts/upload-sourcemaps.sh` baseline (2026-04-30, Phase 5). Under fallback-path:

- Story 1.4 (`vite.config.ts` + plugin integration) → close as won't-ship.
- Story 1.5 (Dockerfile BuildKit secret + compose args) → close as won't-ship (BuildKit secret is only needed for the plugin's auth token at build time; CLI flow injects token at deploy time from `infra/.env`).
- Story 1.6 (`upload-sourcemaps.sh` decoupling + header + RELEASE alignment) → still ships, but its role becomes the **active path**, not the documented manual recovery.

Effectively this delta becomes "tighten existing CLI flow + ship SDK polish + verify/triage scripts" — exactly the pivot the architecture's Risk Mitigation table envisaged for #299, just triggered by a different signal.

**Effort:** zero implementation; just close 2 stories in `epics.md` + `sprint-status.yaml`. **Risk:** Phase 2 backend SDK polish would still be gated on the same triage value metric (≥3 BMAD-triaged issues in 30 days).

## Recommendation

**Option A** is the cleanest long-term solution: it preserves architecture's intent (in-build deterministic upload) AND surfaces a small but real homelab observability config bug. The fix likely promotes into `~/repos/configs/docs/observability-logging-contract.md` as a "homelab GlitchTip config invariant" — strengthening the cross-repo standard.

If operator's appetite for `.190` config debugging is low this cycle, **Option C** is a fully valid scope reduction with no functional regression — the CLI baseline already provides everything Tech Success #1 (real symbolication) requires, just outside the build-time pipeline.

**Option B** is a workaround, not a fix; not recommended unless A and C are both blocked.

## Worktree state at time of writing

The temporary worktree `../3d-portal-phase0` will be removed in Task 7 (next step). No commits landed on `main`. The `_bmad-output/implementation-artifacts/sprint-status.yaml` will be updated next:

- `1-1-phase-0-dry-run-gate: ready-for-dev` → `done` (this story's dry-run completed; outcome documented here).
- `epic-1: in-progress` (no change; remains in-progress).
- `1-4-vite-config-sentry-plugin-integration: backlog` (UNCHANGED — operator decision pending).
- `1-5-dockerfile-buildkit-secret-mount: backlog` (UNCHANGED — operator decision pending).

`epics.md` Epic 1 "Phase 0 branching" note is NOT updated yet — waiting for operator's choice between Options A/B/C in the morning.

## Side artifacts on the GlitchTip server

Two test releases were created during Phase 0:

- `0.1.0+phase0` — created by the plugin attempt before the chunk upload failed. No files associated.
- `0.1.0+phase0-direct` — referenced in the direct-CLI test; modern artifact-bundle flow does not create a per-release file listing, so this release does not show in `releases/?` list (only artifact-bundle exists, lookup by debug-ID).

Both are harmless and can be left alone or cleaned via `curl -X DELETE -H "Authorization: Bearer $TOKEN" 'http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+phase0/'` if operator wants.

---

## Re-run #2 (post-Option-B nginx fix) — 2026-05-09T11:08Z

**Operator decision:** Option B — bump `client_max_body_size` on the public nginx proxy.

**Change applied:** `~/repos/configs/nginx/glitchtip.ezop.ddns.net.conf` got a new regex location block matching `~ ^/api/0/organizations/[^/]+/chunk-upload` with `client_max_body_size 50m;`. The existing `/api/` block (SDK ingestion) stays at 1 MB. Deployed via `~/repos/configs/sync.sh`. nginx reloaded on `.180` and `.190`; `nginx -t` passed on `.190`. Diff committed (or pending commit) in the configs repo only — `3d-portal` repo untouched.

**Re-run setup:** Fresh `git worktree add --detach ../3d-portal-phase0 HEAD`, fresh `npm install --save-dev @sentry/vite-plugin@~5.2.0` (resolved 5.2.1), stub `release.ts` exporting `RELEASE = "0.1.0+phase0r2"`, `vite.config.ts` modified per architecture Decision E/J. Same env exports as the first run.

**Result: HAPPY-PATH ✓**

```
> Bundled 8 files for upload
> Bundle ID: d55db995-745b-52d9-b760-838573eae6e0
> Optimizing completed in 0.004s
> Uploading completed in 0.204s
> Uploaded files to Sentry
> Processing completed in 0.012s
> File upload complete (processing pending on server)
> Organization: homelab
> Projects: 3d-portal
> Release: 0.1.0+phase0r2
> Upload type: artifact bundle

Source Map Upload Report
  Scripts (4 files with debug IDs)
  Source Maps (4 maps with debug IDs)
[sentry-vite-plugin] Info: Successfully uploaded source maps to Sentry
✓ built in 7.24s
```

REST verification: `GET /api/0/projects/homelab/3d-portal/releases/0.1.0+phase0r2/` returned the release metadata with `dateCreated: 2026-05-09T11:08:42.009Z`. `files/` endpoint returned `0` (modern artifact-bundle flow uses debug-ID lookup; per-release file listing is empty by design — same as the direct-CLI test in re-run #1).

**Issue #299 status:** NOT triggered — modern artifact-bundle flow with debug IDs bypasses the legacy `assemble` endpoint entirely. No 404 was observed. The architecture's #299-detection branch becomes academic on this GlitchTip 6.1.6 instance: the plugin uses a pathway #299 doesn't apply to.

**Outcome update (overrides the prior third-category result):**

- [x] **happy-path** — chunk upload 200, source maps + debug IDs uploaded successfully, release registered, build exited 0. **Stories 1.4 and 1.5 PROCEED as originally planned in epics.md.**

**Side effects cleaned:** Test releases `0.1.0+phase0` and `0.1.0+phase0r2` deleted via `DELETE /api/0/projects/homelab/3d-portal/releases/<version>/` (both returned HTTP 204). Worktree removed (`git worktree remove --force`); main repo `git status` clean on `main`.

**Sprint-status updates (next step):**

- `1-1-phase-0-dry-run-gate: done` (already done; no change).
- `1-4-vite-config-sentry-plugin-integration: backlog` (UNGATED — comment removed).
- `1-5-dockerfile-buildkit-secret-mount: backlog` (UNGATED — comment removed).

**`epics.md` updates:**

- Epic 1 "Phase 0 branching" note updated to record happy-path outcome with date stamp.

**Configs repo state:**

- `nginx/glitchtip.ezop.ddns.net.conf` modified, deployed, reloaded successfully.
- Commit suggestion (focused, scope `nginx/glitchtip`):
  ```
  fix(nginx/glitchtip): allow 50m body on chunk-upload path

  @sentry/vite-plugin POSTs multi-MB chunks to /api/0/organizations/<org>/chunk-upload/.
  Public proxy default 1m limit returned HTTP 413 to the plugin during the 3d-portal
  Phase 0 dry-run. Add a regex location block for the chunk-upload path with 50m limit
  while keeping the SDK envelope path at 1m. Auth-gated by Bearer token; rate-limit not
  applied because chunk upload is deploy-time-only.
  ```
  (Operator commits when reviewed; the configs repo's working tree has unrelated dirty docs files from prior dos2unix runs — `git add` only the nginx file to keep this commit focused.)
