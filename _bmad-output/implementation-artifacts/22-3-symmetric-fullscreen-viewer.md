---
title: 'Story 22.3 — Symmetric fullscreen image viewer (TB-037 viewer + TB-022 consumer)'
type: 'feature'
status: 'ready-for-dev'
story_id: '22.3'
epic: 'E22 — Image Tier Pipeline + Symmetric Fullscreen Viewer'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-037 viewer + TB-022 consumer'
fr_ref: 'FR16-VIEWER-1'
architectural_anchor: 'Decision W (consumer side); designer-locked per 22-3-designer-ux-spec.md'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.4-mini per [[feedback_codex_model_routing]] routine FE)'
estimated_effort: '2-3 h NEW component + symmetric mount + visual baselines + tests'
created: '2026-05-24'
---

# Story 22.3 — Symmetric fullscreen image viewer (TB-037 viewer + TB-022 consumer)

Status: ready-for-dev

## Story

As share recipients AND authenticated catalog detail browsers,
I want a "Powiększ / Pełna jakość" fullscreen viewer that opens from the in-page carousel main frame and shows the original-resolution image filling the viewport with a thumb strip for navigation,
so that detail inspection of model photos works at desktop-fullscreen and mobile-tap-to-expand quality regardless of which surface I arrived from (closes TB-037 viewer side; symmetric per operator's 2026-05-24 AskUserQuestion decision).

## Acceptance Criteria

**Designer-locked binding contract**: ALL UX shape decisions (modal pattern, trigger, layout, mobile gestures, i18n keys, dimensions, lazy-import discipline) are AUTHORITATIVE per `_bmad-output/implementation-artifacts/22-3-designer-ux-spec.md`. Implementation MUST follow that spec verbatim — read it FULLY before starting work. ACs below are extracted from the designer spec for traceability; if any AC conflicts with the designer spec, designer spec wins.

1. **AC1 — NEW component `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx`** with lazy-barrel export from `index.ts` mirroring `viewer3d/index.ts` shape per [[feedback_lazy_import_discipline]]:
   ```ts
   // imageViewer/index.ts
   import { lazy } from "react";
   export type { ImageFullscreenViewerProps } from "./types";
   export const ImageFullscreenViewer = lazy(() => import("./ImageFullscreenViewer"));
   ```
   Consumers (ShareCarousel + ModelGallery) wrap in `<Suspense fallback={null}>`. Importing default directly = forbidden.

2. **AC2 — Modal shape: shadcn Dialog mirroring Viewer3DModal** per designer §1. Sizing: `h-[95vh] w-[98vw] max-w-[98vw] p-0`. Backdrop: `bg-background/95 backdrop-blur-sm`. Reject OOTB lightbox libraries (PhotoSwipe / yet-another-react-lightbox) — boring-tech wins.

3. **AC3 — Symmetric surface mount.** Component mounts on BOTH `/share/$token` (anonymous) AND `/catalog/$modelId` (authenticated) per operator 2026-05-24 directive. ImageRenderer prop differs:
   - `/catalog/`: plain `<img src={...} />` (default-auth cookies same-origin).
   - `/share/`: `AnonymousImage` wrapper (credentialless `credentials:"omit"` per NFR10/12).
   Component body identical otherwise.

4. **AC4 — Trigger pattern per designer §2**: main frame is `<button>`-wrapped image (cursor `zoom-in` on desktop, opens on click anywhere); top-right `Maximize2` icon button (lucide) with `bg-gallery-control/40` token (matching existing CardCarousel arrow style); mobile: corner icon always visible; desktop: fade-in on hover/focus (`sm:opacity-0 sm:group-hover:opacity-100`). Keyboard: Enter/Space on focused main frame opens. F shortcut deferred.

5. **AC5 — Fullscreen viewer layout per designer §4**: main image `object-contain` centered + transparent background; thumb strip bottom `h-20 overflow-x-auto` with ~64×64 `?variant=thumb` thumbs and `ring-2 ring-primary` on active; top-right `X` close button always visible (Lucide); top-left counter `{current} / {total}` when `total > 1`; prev/next chevrons mid-height edges hidden when `total === 1`; ESC closes (Dialog default); ArrowLeft/Right navigates.

6. **AC6 — Mobile gestures per designer §5**: tap-to-toggle overlay chrome IN-SCOPE; swipe-left/right between images IN-SCOPE; pinch-to-zoom DEFERRED (note as future work, not TB-040 since that's taken — use TB-042 candidate); swipe-down-to-close DEFERRED (same future-TB-candidate).

7. **AC7 — i18n keys per designer §6** (flat-dotted in `apps/web/src/locales/en.json` + `pl.json`):
   - `catalog.image_viewer.trigger_label` (en: "Open fullscreen", pl: "Powiększ")
   - `catalog.image_viewer.trigger_tooltip` (en: "View full quality", pl: "Pełna jakość")
   - `catalog.image_viewer.close` (en: "Close", pl: "Zamknij")
   - `catalog.image_viewer.prev` (en: "Previous photo", pl: "Poprzednie zdjęcie")
   - `catalog.image_viewer.next` (en: "Next photo", pl: "Następne zdjęcie")
   - `catalog.image_viewer.counter` (both: "{{current}} / {{total}}")
   - `catalog.image_viewer.thumb_label` (en: "Photo {{index}}", pl: "Zdjęcie {{index}}")
   - `catalog.image_viewer.loading` (en: "Loading full image…", pl: "Wczytywanie pełnego obrazu…")
   - `catalog.image_viewer.dialog_title` (en: "Photo gallery", pl: "Galeria zdjęć", sr-only)

8. **AC8 — Image URL construction**: fullscreen frame fetches `?variant=full` (= original blob, no query param OR `?variant=full` literal — verify against Story 22.1 router behavior); thumb strip in viewer uses `?variant=thumb`. For /share/ route, full = `${baseUrl}` (un-varianted) since the backend silent-fallbacks for missing variant. For /catalog/ route, same shape via base URL.

9. **AC9 — Lazy-load chunk verification**: `npm run build` MUST produce a SEPARATE chunk for `ImageFullscreenViewer` (not bundled into main route). Verify by inspecting dist/assets/ output — should see e.g. `ImageFullscreenViewer-<hash>.js` standalone. Without separate chunk, the lazy barrel discipline is broken per [[feedback_lazy_import_discipline]].

10. **AC10 — Visual baselines NEW (per NFR16-VISUAL-VERIFICATION-1)**: Playwright spec creates new baselines:
    - `/catalog/$modelId` with viewer open (4 viewports × light + dark = 8 baselines)
    - `/share/$token` with viewer open (4 viewports × light + dark = 8 baselines, if /share/ visual spec exists; else operator manual verify)
    Hook-context PASS matches standalone.

11. **AC11 — Vitest tests**: 3-5 tests for ImageFullscreenViewer (open/close, ESC, ArrowLeft/Right navigation, counter rendering, lazy-import barrel verification).

12. **AC12 — Codex review CLEAN (gpt-5.4-mini routine FE)**. Round-2 fix-up acceptable.

## Tasks / Subtasks

- [ ] **T1 — Component module + types + barrel** (AC: #1, #2)
  - [ ] T1.1 — Create `apps/web/src/modules/catalog/components/imageViewer/` directory.
  - [ ] T1.2 — `types.ts` exporting `ImageFullscreenViewerProps` interface (designer §7 signature).
  - [ ] T1.3 — `ImageFullscreenViewer.tsx` default export — shadcn Dialog wrapper following designer §1-5 layout.
  - [ ] T1.4 — `index.ts` lazy barrel mirroring `viewer3d/index.ts`.

- [ ] **T2 — i18n keys** (AC: #7)
  - [ ] T2.1 — Append 9 keys to `apps/web/src/locales/en.json` under `catalog.image_viewer.*`.
  - [ ] T2.2 — Mirror in `pl.json` with Polish diacritics.

- [ ] **T3 — Symmetric mount: ShareCarousel** (AC: #3)
  - [ ] T3.1 — `apps/web/src/routes/share/$token.tsx:ShareCarousel`: add `[fullscreenOpen, setFullscreenOpen]` state; wrap main frame in `<button onClick={() => setFullscreenOpen(true)}>`; conditionally render `<Suspense fallback={null}><ImageFullscreenViewer ... /></Suspense>` with `renderImage={AnonymousImage}`.

- [ ] **T4 — Symmetric mount: ModelGallery** (AC: #3)
  - [ ] T4.1 — `apps/web/src/modules/catalog/components/ModelGallery.tsx`: same shape as T3.1 but `renderImage={({ src, alt, className }) => <img src={src} alt={alt} className={className} />}` (plain img for authenticated route).

- [ ] **T5 — Tests** (AC: #11)
  - [ ] T5.1 — NEW `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.test.tsx` with 3-5 tests.

- [ ] **T6 — Pre-merge gates** (AC: #9)
  - [ ] T6.1 — `npm run typecheck` clean.
  - [ ] T6.2 — `npm run lint` clean.
  - [ ] T6.3 — `npx vitest run` PASS.
  - [ ] T6.4 — `npm run build` — verify ImageFullscreenViewer chunk is SEPARATE (grep dist/assets/ for `ImageFullscreenViewer-*.js`).
  - [ ] T6.5 — Playwright spec runs; visual baselines regen or NEW.

- [ ] **T7 — Commit + Codex + deploy** (orchestrator)
  - [ ] T7.1 — `feat(catalog,share): symmetric fullscreen image viewer (Story 22.3, TB-037 viewer)`.
  - [ ] T7.2 — Codex review gpt-5.4-mini.
  - [ ] T7.3 — Auto-deploy.
  - [ ] T7.4 — Operator hands-on verify post-deploy.

## Dev Notes

**READ THE DESIGNER UX SPEC**: `_bmad-output/implementation-artifacts/22-3-designer-ux-spec.md`. That document is the authoritative source for all UX decisions; this spec extracts ACs for traceability. The designer spec includes paste-ready code sketches for the barrel, props interface, and consumer-site mount.

### Lazy barrel verification

After build, check:
```bash
ls apps/web/dist/assets/ | grep -i "ImageFullscreenViewer"
# expected: ImageFullscreenViewer-<hash>.js standalone chunk
```

If missing → import shape broken; consumer is importing default directly instead of via the lazy barrel.

### Symmetric surface — single component, prop-injected renderer

Designer §7 explicitly: "Component body identical otherwise. Both surfaces get identical layout, identical gestures, identical i18n, identical keyboard handling. Operator's 'symmetric' decision is enforced by the single component, not by parallel mounts."

The `renderImage: ImageRenderer` prop is the cookie-credential boundary. Don't duplicate the viewer into share-vs-catalog variants.

### What NOT to touch

- `Viewer3DInline` / `Viewer3DModal` — different surface (3D, not image).
- `srcOverride` pattern from Story 20.3 — that's for Viewer3DInline; ImageFullscreenViewer doesn't need it.
- Story 23.1 `shareBlobCache` invalidation — unchanged.
- ModelCard card-grid — stays `?variant=thumb` per Story 20.1.

## File List

**NEW (4):**
- `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx`
- `apps/web/src/modules/catalog/components/imageViewer/index.ts`
- `apps/web/src/modules/catalog/components/imageViewer/types.ts`
- `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.test.tsx`

**MODIFIED (4):**
- `apps/web/src/routes/share/$token.tsx` — ShareCarousel mount point
- `apps/web/src/modules/catalog/components/ModelGallery.tsx` — ModelGallery mount point
- `apps/web/src/locales/en.json` — +9 i18n keys
- `apps/web/src/locales/pl.json` — +9 i18n keys

**Diff stats expected:** ~250-400 LOC new + ~30-50 LOC modified + visual baselines.

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Typecheck | `cd apps/web && npm run typecheck` | Exit 0 |
| Lint | `cd apps/web && npm run lint` | Exit 0 |
| Vitest | `cd apps/web && npx vitest run` | All PASS |
| Build | `cd apps/web && npm run build` | Exit 0; ImageFullscreenViewer in separate chunk |
| Lazy chunk | `ls dist/assets/ \| grep ImageFullscreenViewer` | Standalone .js + .js.map |
| Visual | `npx playwright test --update-snapshots -g "catalog-detail\|share"` | Baselines created/regen'd |
| Codex review | `codex review --commit <SHA> -c review_model="gpt-5.4-mini"` | CLEAN or fix-up |

## References

- **Designer UX spec (AUTHORITATIVE)**: `_bmad-output/implementation-artifacts/22-3-designer-ux-spec.md`
- [Init 16 SCP §4.1 Story 22.3](sprint-change-proposal-2026-05-24-init16.md#41-epic-e22--image-tier-pipeline--symmetric-fullscreen-viewer)
- [prd.md § FR16-VIEWER-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep)
- Backend handshake shipped: Story 22.1 a04a61f + 05ad8f0 (variant routing on both surfaces)
- Memory: [[feedback_lazy_import_discipline]], [[feedback_codex_model_routing]], [[feedback_frontend_visual_verification]], [[feedback_pre_merge_gate_checklist]], [[feedback_auth_boundary_contract_audit]] (for the credentialless boundary preservation)
- Existing patterns: `apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx` + `viewer3d/index.ts` lazy barrel
- shadcn Dialog: `apps/web/src/components/ui/dialog.tsx` (presumed location)

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
