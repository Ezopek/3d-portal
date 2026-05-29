# Story 22.3 — Designer UX Spec (Symmetric Fullscreen Image Viewer)

**Produced by:** Sally (bmad-agent-ux-designer persona, invoked via general-purpose subagent)
**Date:** 2026-05-24
**Context:** Init 16 SCP §3.4 designer engagement (gated NFR16-SCOPE-DESIGNER-GATE-1)
**Operator decisions locked at SCP-time:** symmetric surface (share + catalog detail), TB-022 already shipped via Story 20.3, lazy import discipline required
**Purpose:** Paste-ready UX spec section for Story 22.3 spec authoring. Maintained as a separate artifact so it survives potential context summarization between SCP approval and Story 22.3 `bmad-create-story` invocation.

---

## UX Spec — Symmetric Fullscreen Image Viewer (Story 22.3)

### Component naming
`ImageFullscreenViewer.tsx` under `apps/web/src/modules/catalog/components/imageViewer/`, exported via a **lazy barrel** `index.ts` that mirrors `viewer3d/index.ts`:

```ts
// apps/web/src/modules/catalog/components/imageViewer/index.ts
import { lazy } from "react";
export type { ImageFullscreenViewerProps } from "./types";
export const ImageFullscreenViewer = lazy(() => import("./ImageFullscreenViewer"));
```

Consumers (`CardCarousel`, `ShareCarousel`) wrap the rendered viewer in `<Suspense fallback={null}>`. Importing the default directly is forbidden per `[[feedback_lazy_import_discipline]]`.

### 1. Modal pattern — **custom, matching Viewer3DModal**
Reuse shadcn `Dialog`/`DialogContent` exactly like `Viewer3DModal.tsx` does. Rejected `yet-another-react-lightbox` / `PhotoSwipe`: an extra ~30-60 KB dep that re-implements focus-trap, theme tokens, and i18n we already have. The Story-22.3 surface is ~150 LOC of `<img>` + thumb-strip + keyboard handler; boring-tech bias wins. Same `Dialog` primitive also guarantees identical focus management, ESC handling, and dark-mode token wiring as the 3D viewer.

### 2. Trigger pattern — **click main frame + corner expand icon, mirrored desktop/mobile**
- **Main frame is a `<button>`-wrapped image** (cursor: zoom-in on desktop). Click anywhere on the main image opens fullscreen.
- **Corner affordance** — top-right `Maximize2` icon button (lucide), `bg-gallery-control/40` to match existing arrow buttons. Always visible on mobile (touch users can't infer click-to-zoom); fade-in on hover/focus on desktop (`sm:opacity-0 sm:group-hover:opacity-100`), matching `CardCarousel` arrow pattern.
- **Keyboard** — `Enter`/`Space` on the focused main frame opens (free with the `<button>` wrapper); `F` shortcut deferred (low ROI, no precedent in repo).
- **No separate "Powiększ" header button** — operator's verbal framing is the conceptual trigger, not a literal CTA. The icon's aria-label and tooltip carry the Polish/English label.

### 3. Gallery tier longest-edge target — **1920 px**
Rationale: the in-page carousel main frame on `/catalog/$modelId` renders inside a content column that maxes at ~720 CSS px on desktop, but high-DPR laptops (MacBook 2x) push the physical bitmap demand to ~1440 px on the longest edge. The `/share/$token` frame uses `aspect-[4/3]` at full content width (~1200 CSS px in centered layout) → ~2400 px on 2x DPR — but at that tier we're already deep in diminishing-returns territory for WebP quality vs payload. **1920 px** is the cleanest tradeoff: covers 1080p fullscreen-but-not-zoomed and all 2x DPR laptop main frames; falls short only on 4K/5K monitors viewing the gallery frame at full bleed, which is exactly the case the **fullscreen** tier (original) handles. Payload stays in the 150-500 KB band per TB-037.

### 4. Fullscreen viewer dimensions + layout
- **Frame fills viewport with thin backdrop padding** — `DialogContent` uses `h-[95vh] w-[98vw] max-w-[98vw] p-0` (slightly more generous than `Viewer3DModal`'s `h-[90vh] w-[95vw]` because there are no side panels competing for space).
- **Main image** — `object-contain` inside `flex-1`, centered, transparent background revealing the dialog backdrop (`bg-background/95 backdrop-blur-sm` on the overlay).
- **Thumb strip** — bottom-fixed horizontal row, `h-20`, `overflow-x-auto`, ~64×64 px thumbs (`?variant=thumb`), active thumb gets `ring-2 ring-primary`. Same component shape as `ShareCarousel`'s thumb strip — visual symmetry between in-page and fullscreen surfaces.
- **Close button** — top-right `X` icon (lucide), **always visible**, no idle-fade. Matches `Viewer3DModal` precedent and avoids the "where did the close button go" mobile trap.
- **Counter** — top-left `{current} / {total}`, `text-sm text-muted-foreground bg-background/60 rounded px-2 py-1`. Only renders when `total > 1`.
- **Prev/Next chevrons** — left/right edge mid-height, same `bg-gallery-control/40` token pair as `CardCarousel`. Hidden when `total === 1`.
- **Keyboard** — `Esc` closes (Dialog default), `ArrowLeft`/`ArrowRight` navigate (mirrors `Viewer3DModal:onKey` lines 202-209). Focus-trap inherited from Dialog.

### 5. Mobile gesture support
| Gesture | Story 22.3 | Follow-up (Init 17) | Rationale |
|---|---|---|---|
| Tap main image to toggle overlay chrome | **In-scope** | — | Cheap (boolean state + opacity transition); maximises image real-estate without extra deps |
| Swipe left/right between images | **In-scope** | — | One `onTouchStart`/`onTouchEnd` handler, ~20 LOC, expected by users — leaving it out breaks the "feels like a phone gallery" baseline |
| Pinch-to-zoom | Deferred | **TB-040 candidate** | Requires `react-zoom-pan-pinch` or hand-rolled transform math; OS-native zoom (double-tap on iOS Safari, browser zoom on Android) works as the fallback for now |
| Swipe-down-to-close | Deferred | **TB-040 candidate** | Conflicts naively with thumb-strip horizontal scroll; needs gesture-disambiguation work; Esc / X-button cover the desktop + tablet cases |

> **Note:** Designer's original output referenced "TB-038 Init 17" for pinch-zoom + swipe-down-close deferrals; TB-038 is already taken (mobile photo-reorder touch-action — Story 25.1). Renamed to new TB-040 candidate (to be filed at Story 22.3 close-out if operator surfaces interest).

### 6. i18n keys (flat-dotted, matching repo convention)

| Key | en | pl |
|---|---|---|
| `catalog.image_viewer.trigger_label` | "Open fullscreen" | "Powiększ" |
| `catalog.image_viewer.trigger_tooltip` | "View full quality" | "Pełna jakość" |
| `catalog.image_viewer.close` | "Close" | "Zamknij" |
| `catalog.image_viewer.prev` | "Previous photo" | "Poprzednie zdjęcie" |
| `catalog.image_viewer.next` | "Next photo" | "Następne zdjęcie" |
| `catalog.image_viewer.counter` | "{{current}} / {{total}}" | "{{current}} / {{total}}" |
| `catalog.image_viewer.thumb_label` | "Photo {{index}}" | "Zdjęcie {{index}}" |
| `catalog.image_viewer.loading` | "Loading full image…" | "Wczytywanie pełnego obrazu…" |
| `catalog.image_viewer.dialog_title` | "Photo gallery" | "Galeria zdjęć" (sr-only) |

Namespace `catalog.image_viewer.*` is shared by both mounts — symmetric surface, symmetric strings. The `share.view.carousel_*` keys stay scoped to the in-page share carousel (existing); they are NOT reused for the fullscreen viewer to keep auth-gate / share-gate code paths independent of i18n shape.

### 7. Symmetric-surface differences
- **Image-fetch wrapper differs, viewer body is identical.** On `/catalog/$modelId` the viewer renders `<img src={`/api/models/${modelId}/files/${id}/content?variant=full`} />` directly (browser default credentials = same-origin cookies). On `/share/$token` it routes through `AnonymousImage` (lines 135-168 of `share/$token.tsx`) so blob fetches stay `credentials:"omit"` per the NFR10/12 credentialless contract `[[feedback_auth_boundary_contract_audit]]`. Pass the image-renderer in as a prop:

  ```ts
  type ImageRenderer = (props: { src: string; alt: string; className?: string }) => JSX.Element;
  interface ImageFullscreenViewerProps {
    sources: readonly { fullUrl: string; thumbUrl: string; alt: string }[];
    initialIndex: number;
    onClose: () => void;
    renderImage: ImageRenderer; // <-- AnonymousImage on /share, plain <img> on /catalog
  }
  ```

- **No feature divergence.** Both surfaces get identical layout, identical gestures, identical i18n, identical keyboard handling. Operator's "symmetric" decision is enforced by the single component, not by parallel mounts.
- **No auth gate inside the viewer.** Both mounts have already crossed their auth boundary by the time the viewer opens; the viewer trusts its inputs.

### 8. Lazy-load discipline
- Barrel pattern above (`lazy(() => import(...))`) — verified pattern from `apps/web/src/modules/catalog/components/viewer3d/index.ts:6-7`.
- Consumer site:

  ```tsx
  const [fullscreenOpen, setFullscreenOpen] = useState(false);
  // ...
  {fullscreenOpen && (
    <Suspense fallback={null}>
      <ImageFullscreenViewer
        sources={sources}
        initialIndex={activeIdx}
        onClose={() => setFullscreenOpen(false)}
        renderImage={AnonymousImage} // or plain <img/> for /catalog
      />
    </Suspense>
  )}
  ```
- Verification gate: `npm run build` must show `ImageFullscreenViewer` in a **separate chunk**, not bundled into the main catalog/share routes — per `[[feedback_lazy_import_discipline]]` round-1 precedent on Story 19.7. Add a build-output assertion to the story's Test plan.
- Visual baseline: per `[[feedback_frontend_visual_verification]]`, new Playwright visual snapshots for (a) `/catalog/$modelId` with viewer open, (b) `/share/$token` with viewer open, light + dark, desktop + mobile (4 × 2 = 8 baselines). Reuse existing share-view snapshot harness.

### Rationale
A custom shadcn-Dialog viewer matching `Viewer3DModal`'s aesthetic keeps the dependency graph boring and the visual language already-familiar to recipients who saw the 3D viewer in the same session. Per `[[feedback_share_view_scope_boundary]]` the share view stays a TERMINUS — TB-037 is admitted only as the **image-quality exception**, so we cap ambition at "feels like a phone gallery" (tap-to-zoom, swipe-between, swipe-to-close-and-pinch deferred). Symmetric surface = single component + injected image-renderer; the cookie-credential boundary stays at the renderer prop, not duplicated through parallel viewer trees.

---

## Key files referenced (for Story 22.3 spec implementation map)

- `/home/ezop/repos/3d-portal/apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx` — Dialog sizing + keyboard handler precedent (lines 224-228, 163-210)
- `/home/ezop/repos/3d-portal/apps/web/src/modules/catalog/components/viewer3d/index.ts` — lazy barrel pattern to mirror
- `/home/ezop/repos/3d-portal/apps/web/src/routes/share/$token.tsx` — `AnonymousImage` (lines 135-168) and `ShareCarousel` (lines 184-267) for credentialless wrapper + thumb-strip baseline
- `/home/ezop/repos/3d-portal/apps/web/src/ui/custom/CardCarousel.tsx` — `bg-gallery-control/40` token usage and `sm:group-hover:opacity-100` reveal pattern (lines 169, 178)
- `/home/ezop/repos/3d-portal/apps/web/src/styles/theme.css:54-55` — `--color-gallery-control` / `--color-gallery-control-foreground` tokens (already light+dark)
- `/home/ezop/repos/3d-portal/apps/web/src/locales/en.json` + `pl.json` — flat-dotted-key convention (`viewer3d.*`, `share.view.*`)

## Updates against Story 22.1 spec authoring

- **Gallery tier longest-edge: 1920px** — locks Story 22.1 AC1 default. Designer reasoning: covers 1080p fullscreen-but-not-zoomed + all 2x DPR laptop main frames; 4K/5K full-bleed falls through to fullscreen-tier (original blob) handler.
