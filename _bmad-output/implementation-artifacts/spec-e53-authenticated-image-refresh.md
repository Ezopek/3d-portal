---
title: 'Catalog lightbox images recover from access-session expiry'
type: 'bugfix'
created: '2026-08-02'
baseline_commit: 'ee0fe2a136873675eabf5eb039dc8fd70502da2f'
status: 'approved-for-commit'
review_loop_iteration: 1
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `portal_access` lives 10 minutes; the catalog lightbox stays open far longer. Its full-resolution frames are native `<img src="/api/models/.../content?variant=full">` loads, which cannot see `apiFetch`'s `401 → refreshAccessToken() → retry` path, so once the cookie expires every subsequent photo fails with the inline `Nie udało się wczytać zdjęcia.` and never recovers — measured in production on 2026-08-02: ten `?variant=full` 401s at 19:36:41–19:36:55 while the operator navigated the viewer, against a refresh session that had successfully refreshed twice ten minutes earlier.

**Approach:** Give the authenticated catalog renderer a bounded, error-driven recovery: when a native image load fails, fetch the same URL through a new credentialed binary helper that reuses the existing `refreshAccessToken()` singleton (one refresh, one retry), and swap the recovered blob in as an object URL. The happy path stays a plain native `<img>`, byte-identical to today.

## Boundaries & Constraints

**Always:**
- Reuse the existing `refreshAccessToken()` singleton in `@/lib/refresh` and the existing 401 `detail` contract (`access_expired` / `missing_access` only).
- Recovery is credentialed (`credentials: "include"` + `X-Portal-Client: web`) and same-origin `/api/...` only.
- At most ONE recovery attempt per image URL: ≤1 refresh, ≤1 retry fetch. No loop, no storm.
- Object URLs are revoked on src change and on unmount; no `setState` after unmount; StrictMode double-effect leaves zero leaked URLs.
- The `ImageFullscreenViewer` `renderImage` / `renderThumb` consumer boundary, its readiness probe, watchdog, zoom/gesture engine, a11y and i18n key set stay untouched.

**Ask First:**
- Any change to `ImageFullscreenViewer.tsx`, `apps/web/src/ui/dialog.tsx`, the viewer's toolbar/chrome visibility, or any new i18n key.
- Making the same fix cover the non-fullscreen `gallery-main` / `gallery-thumb` images on the detail page (different exposure profile — see Design Notes).

**Never:**
- Do not touch `apps/web/src/routes/share/$token.tsx` or `shareBlobCache.ts`; `/share` stays `credentials: "omit"` (NFR10-SHARE-SECURITY-1). No `/api/share` fallback from the authenticated catalog.
- Do not pretend `api<T>()` returns blobs — the binary path is a separate, explicitly-typed export.
- Do not refresh on every image error (refresh tokens rotate; a blind refresh on a 404 would burn a rotation).
- No toolbar/chrome behavior change (operator-deferred), no unrelated refactor, no new locale keys.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Happy path | Valid access cookie | Native `<img src={url}>` loads; zero `fetch` calls from the renderer | N/A |
| Access expired, refresh valid | `<img>` fires `error`; `GET url` → 401 `access_expired` | One `refreshAccessToken()`, one retry of the same URL, blob → object URL swapped into the same `<img>`; viewer returns to `ready` | N/A |
| `missing_access` | Same, detail `missing_access` | Identical to above | N/A |
| Refresh rejected (dead session) | 401 `access_expired`, `POST /api/auth/refresh` → 401 | No retry fetch; `<img>` keeps the original src; viewer's existing inline error state stands | Rejection swallowed at the component; no unhandled rejection |
| Retry still 401 | Refresh 200, retry → 401 | Terminal after exactly 2 content fetches; no third attempt | Same as above |
| Non-refreshable failure | `GET url` → 404 / 500 / network throw | Terminal immediately; `refreshAccessToken()` NOT called | Same as above |
| Navigate away mid-recovery | src changes / viewer unmounts while fetch in flight | Object URL revoked, no state update, no leak | N/A |

</frozen-after-approval>

## Code Map

- `apps/web/src/lib/api.ts` -- `api<T>()`'s 401 `detail` → refresh → single-retry contract; source of `ApiError`. Read-only reference.
- `apps/web/src/lib/refresh.ts` -- `refreshAccessToken()` in-flight singleton. Reused as-is.
- `apps/web/src/lib/api-blob.ts` -- NEW. `fetchApiBlob(url)`: credentialed binary fetch with the same 401-detail refresh-and-retry-once contract.
- `apps/web/src/modules/catalog/components/AuthenticatedImage.tsx` -- NEW. Native `<img>` that self-heals one failed load through `fetchApiBlob` + object URL.
- `apps/web/src/modules/catalog/components/ModelGallery.tsx` -- `renderImage` at `:225-227` is the only production wiring change.
- `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` -- consumer of `renderImage`; readiness probe `:521-547`, capture-phase `load`/`error` `:553-572`. Read-only.
- `apps/web/src/routes/share/$token.tsx`, `shareBlobCache.ts` -- the credentialless boundary this change must not disturb. Read-only.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/lib/api-blob.test.ts` -- RED first: cover every I/O Matrix row at the helper level (credentials/header, refresh-once, retry-once, no-refresh-on-non-401, terminal states, concurrent callers share one refresh) -- the fetch contract is where the bug lives.
- [x] `apps/web/src/lib/api-blob.ts` -- implement `fetchApiBlob(url: string): Promise<Blob>`; throw `ApiError` on terminal failure -- reuses the wrapper's error surface rather than a parallel one.
- [x] `apps/web/src/modules/catalog/components/AuthenticatedImage.test.tsx` -- RED first: no fetch on the happy path, one recovery per src, object-URL create/revoke balance under src change + unmount + StrictMode, no `/api/share` request.
- [x] `apps/web/src/modules/catalog/components/AuthenticatedImage.tsx` -- implement the renderer.
- [x] `apps/web/src/modules/catalog/components/ModelGallery.test.tsx` -- extend: opening fullscreen and failing the main frame drives the credentialed recovery of the `?variant=full` URL.
- [x] `apps/web/src/modules/catalog/components/ModelGallery.tsx` -- pass `AuthenticatedImage` as the viewer's `renderImage` (as a rendered element, not by reference).
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- ledger the residuals this fix knowingly leaves open.

**Acceptance Criteria:**
- Given a valid session, when the lightbox renders a photo, then the renderer issues no `fetch` at all and the DOM `<img>` carries the plain `/api/models/...` URL (today's behavior, unchanged).
- Given the access cookie expired mid-session and a valid refresh session, when the photo's native load fails, then exactly one refresh and one retry occur and the photo appears, without the user reloading the page or re-logging in.
- Given a dead session, when recovery runs, then it stops after the failed refresh with the viewer's existing error state and no further requests.
- Given any recovery path, when the viewer unmounts or the user navigates to another photo, then every created object URL is revoked and no state update targets an unmounted component.
- Given the whole change, when `git diff --stat` is read, then `$token.tsx`, `shareBlobCache.ts`, `ImageFullscreenViewer.tsx`, `types.ts` and both locale files are absent from it.

## Spec Change Log

## Design Notes

**Why error-driven and not always-blob.** Routing every full frame through `fetch → blob → objectURL` would (a) move `/catalog` full images off the viewer's `!initial.complete` probe branch onto the never-mounted-`<img>` branch, re-arming the 15 s readiness watchdog that ruling DN-2 deliberately narrowed away — a 4–8 MB original on mobile would be announced as a terminal failure while still downloading; (b) lose progressive decoding on exactly the low-end Android class this epic is being fixed for; (c) hold every viewed original in memory. Error-driven recovery keeps the happy path a native `<img>`, so the probe, the watchdog and the decode path are all untouched, and the cost is paid only by the images that actually failed.

**Why a probe fetch rather than refreshing on `error`.** An `<img>` error event carries no status. Refresh tokens rotate on every use and reuse triggers family invalidation, so a blind refresh on any image error (404, deleted file, network blip) is unacceptable. One credentialed fetch of the same URL is what turns "the image broke" into "the image broke with `401 access_expired`".

**Why the renderer is passed as an element, not by reference.** `renderImage` is *called*, not mounted (`types.ts:23`), so `renderImage={AuthenticatedImage}` would register its hooks in the viewer's own fiber — the mechanism behind the open DN-4 `/share` residual, and a hook-count that varies with `sources.length` when the same renderer feeds the strip. `renderImage={(p) => <AuthenticatedImage {...p} />}` gives each image its own fiber and its own effect ordering.

**Accepted trade-off.** During recovery the viewer's inline error chip is visible for the duration of probe + refresh + retry, then clears on the recovered `load`. Today that state is permanent; this makes it transient and self-healing. Suppressing the flash would require changing the viewer's readiness contract (Ask First / out of scope).

## Verification

**Commands:**
- `npm run test -- src/lib/api-blob.test.ts src/modules/catalog/components/AuthenticatedImage.test.tsx src/modules/catalog/components/ModelGallery.test.tsx` (from `apps/web/`) -- GREEN after the Aider follow-up: 3 files / 32 tests passed.
- `npm run test` (from `apps/web/`) -- GREEN: 156 files / 1165 tests passed.
- `npm run lint` + `npm run typecheck` (from `apps/web/`) -- GREEN; only the repo's pre-existing React-version ESLint warning printed.
- `npm run test:visual` (from `apps/web/`) -- GREEN: 826 passed / 50 skipped, zero snapshot updates.
- `infra/scripts/check-all.sh` (repo root, logged under `.hermes/run-logs/check-all-t_d8ab5ba3-*.log`) -- GREEN: 16/16 stages passed; summary printed `all green.`.
- `git diff --stat` -- PASS: `$token.tsx`, `shareBlobCache.ts`, `ImageFullscreenViewer.tsx`, `imageViewer/types.ts`, and `locales/*.json` do not appear.

## Review

- Native repo-local Claude/BMAD authored the spec/code/tests on branch `fix/E53-authenticated-image-refresh`; the long run ended at `error_max_turns` after writing the implementation and running controller-observed gates, so final gate evidence and this close-out stamp are controller-verified rather than Claude-self-reported.
- Routine independent Aider diff review initially requested extra rapid-src-change coverage. Follow-up added `AuthenticatedImage.test.tsx` coverage for an in-flight recovery resolving after `src` changes.
- Second Aider diff review verdict: `APPROVE`; no critical or important blockers.
