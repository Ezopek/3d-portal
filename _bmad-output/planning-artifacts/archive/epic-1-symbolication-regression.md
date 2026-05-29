# Epic 1 Production Symbolication Regression — Discovered AND Resolved by Story 3.1 Verify Ritual

**Discovered:** 2026-05-09 during Story 3.1 dev cycle (commit `a1b76a4`)
**Resolved:** 2026-05-09 (commit `2f02d7e` + homelab GlitchTip compose fix)
**Severity:** HIGH — defeated Epic 1's primary value (production-readable stack traces)
**Status:** **CLOSED.** The verify ritual now exits 0 with top frame `apps/web/src/main.tsx`. Both the homelab GlitchTip volume-mount bug AND the source-map path-normalization gap are fixed.

## Resolution summary

1. **Homelab GlitchTip stack fix (out-of-repo, on `.190`):** `glitchtip-worker` was missing the `glitchtip-uploads` volume mount that the `glitchtip` web container has. Worker's `assemble_artifacts_task` failed with `FileNotFoundError: '/code/uploads/file_blobs/...'` whenever it tried to assemble uploaded chunks. Result: `sourcecode_debugsymbolbundle` table stayed empty no matter how many chunks the plugin pushed. Fix applied to `/mnt/raid/docker-compose/glitchtip.yml` on `.190`:
   ```yaml
   glitchtip-worker:
     # ...
     volumes:
       - glitchtip-uploads:/code/uploads
   ```
   Restart with the env file: `docker compose --env-file glitchtip.env -f glitchtip.yml up -d`. (Restarting WITHOUT `--env-file` blanks `SECRET_KEY` and `DATABASE_URL` password — recoverable but messy.) After this fix, `assemble_artifacts_task` succeeds and the bundles table populates as expected.

2. **3d-portal repo fix (commit `2f02d7e`):** even after the worker had access to chunks, GlitchTip surfaced resolved frames as `../src/main.tsx` (relative path from `dist/assets/`). NFR-R1's regex `^apps/web/src/.+\.tsx?$` rejected the prefix mismatch. Added `build.rollupOptions.output.sourcemapPathTransform` in `apps/web/vite.config.ts` that strips leading `../` segments and anchors app-source paths at `apps/web/<...>`. Vendor paths under `node_modules/` are left untouched.

## Verification

`bash infra/scripts/verify-symbolication.sh` post-fix:
```
→ Triggering smoke event: smoke.run_id=0d79704b-6af8-43b6-b37c-062a331e5213
→ Polling GlitchTip REST for matching event (budget: 30s)
→ Matched issue id=41; fetching latest event
✓ verify OK — top frame: apps/web/src/main.tsx, release: 0.1.0+76527ab
```
exit 0. `infra/.last-verify` carries `2026-05-09T21:23:06Z<TAB>OK<TAB>0.1.0+76527ab`.

`SELECT COUNT(*) FROM sourcecode_debugsymbolbundle;` post-fix: **4** (one per code-split chunk).

## Original investigation notes (preserved for context)

## Summary

`verify-symbolication.sh` consistently exits 1 against production with `top frame regex mismatch (got: /assets/index-XXXXX.js)`. The deployed bundle is minified and the symbolicator does NOT resolve frames to `apps/web/src/<...>.tsx:<line>`.

This contradicts Story 1.5's smoke-test claim that debug-IDs were injected and Story 1.6's claim that source maps were uploaded successfully via `@sentry/vite-plugin`.

## Symptoms

GlitchTip API for issue id=35 (latest verify-triggered event) returns:

```json
{
  "filename": "/assets/index-BiOzEUWi.js",
  "function": "?",
  "absPath": "https://3d.ezop.ddns.net/assets/index-BiOzEUWi.js",
  "lineNo": 182,
  "colNo": 53236,
  "module": null,
  "context": []
}
```

- `filename` is the public asset path, not the source TS path.
- `function` is `"?"` (unresolved).
- `module` is `null`.
- `context` is empty (no source-context lines).
- Tag `release: 0.1.0+a1b76a4` is correctly attached on the EVENT side; the SDK config is fine.

## What works

- ✅ Bundle has `sentryDebugId` markers (Story 1.5 verified, repeatable: `grep -c sentryDebugId apps/web/dist/assets/*.js` returns positive).
- ✅ Build-time plugin upload reports success (`[sentry-vite-plugin] Info: Successfully uploaded source maps to Sentry`, four chunks per build).
- ✅ Event ingest works: GlitchTip receives the event with all expected tags (`smoke.run_id`, `release`, `service`, `environment`, etc.).
- ✅ Release tag matches deployed bundle: `0.1.0+a1b76a4` for the current deploy.

## What's broken

- ❌ GlitchTip's symbolicator never matches the deployed bundle's debug-IDs to any uploaded artifact bundle. Top frame stays minified. Re-fetching the event 30s later shows the same minified frame — not a transient processing-lag.

## Likely root causes (untriaged)

1. **Chunk-upload "processing pending" never completes server-side.** Build log line: `> File upload complete (processing pending on server)`. GlitchTip 6.1.x may have a background processor that's failing silently, leaving artifact bundles in a pending state.
2. **Debug-ID format mismatch between the bundle and the upload.** `@sentry/vite-plugin` 5.2.x emits one debug-ID format; GlitchTip 6.1.x's symbolicator may expect a different format. Phase 0 (Story 1.1) tested smoke locally on `:8800`, but post-deploy on `:443/nginx` may differ.
3. **Release association.** Source maps may have been uploaded under a different `release` than the deployed bundle's runtime release. Plugin's `release: { name: ${PKG_VERSION}+${GIT_COMMIT} }` reads at vite-config evaluation time on the dev box; the runtime SDK reads `RELEASE` from the bundled `release.ts` evaluated under the same `PKG_VERSION`+`GIT_COMMIT` from build args. They SHOULD match — but worth verifying via API.
4. **Source-map path normalization.** The SDK reports `filename: /assets/index-X.js`; the uploaded source-map's `sources` array may use a different path prefix that doesn't reconcile.

## Suggested investigation steps

1. Check GlitchTip's release `0.1.0+a1b76a4` — is it present? Does it have artifact bundles?
   ```bash
   set -a; source infra/.env; set +a
   curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
     "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+a1b76a4/" | jq .
   curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
     "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+a1b76a4/files/" | jq .
   ```
2. Check GlitchTip's debug-files endpoint:
   ```bash
   curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
     "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/files/debug-files/" | jq '.[] | {debugId, fileName, fileFormat}'
   ```
3. Inspect a deployed JS bundle's `sentryDebugId` value vs GlitchTip's debug-files list — should match exactly.
4. Check GlitchTip server logs (`docker compose logs --tail=200 glitchtip-worker` on .190) for source-map-processing errors.

## Why ship Story 3.1 anyway

Story 3.1's value proposition is the verify ritual itself. The script is working perfectly:

1. ✅ Triggers smoke event via headless chrome (real JS execution).
2. ✅ Polls GlitchTip REST within 30s budget.
3. ✅ Matches the event by `smoke.run_id` tag.
4. ✅ Extracts the top frame.
5. ✅ Asserts the regex.
6. ✅ Writes `.last-verify FAILED` on mismatch (correctly identifies the regression).
7. ✅ POSTs synthetic alarm event with `deploy.verification=failed` tag.
8. ✅ Exits 1.

This is the THREE-SIGNAL FAILURE MODEL (NFR-R3) catching a real regression that would have stayed silent without the verify ritual. Story 3.1 succeeded at its core mission.

If Story 3.1 had been blocked on Epic 1's symbolication being green, the regression would have stayed undetected. Verify-as-tripwire is exactly the discipline that surfaces such issues early.

## Follow-up routing

- **Owner:** Epic 1 retrospective OR a new bugfix story (`fix/epic-1-symbolication-regression`) if work proceeds before retro.
- **Branch:** `fix/<topic>` per project convention.
- **Verify outcome:** A successful fix means `bash infra/scripts/verify-symbolication.sh` exits 0 with `OK` line — no special test needed; the verify ritual IS the regression test.
