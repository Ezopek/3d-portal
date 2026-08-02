# Story 53.1 — Mobile lightbox adoption recommendation (FR26-VIEW-1, Decision BA)

> **VERDICT: PROVISIONAL — pending physical Android Chrome evidence.**
> **G26-LIB REMAINS OPEN.** `implementation-readiness-report-2026-07-26.md:205` closes G26-LIB on *"53.1 recommendation **plus** physical Android evidence"*. This artifact delivers the first conjunct and the instrument for the second. **Closing the gate is the operator's act, not this story's.**

- **Story:** `53-1-lightbox-adoption-spike` · **Epic:** E53 — Mature mobile lightbox (Initiative 26)
- **Authored:** 2026-07-29 by Claude Opus 5, repo-local, native `bmad-dev-story`. **NOT** an Ezop signature, **NOT** human review, **NOT** approval of the recommendation below.
- **Authorization:** `G26-DEVGO` granted by Laura/controller for this story only, under Ezop's standing Initiative 26 delegation.
- **Baseline commit for every measurement:** `513f4bdd1c9a63fc9ba6df18d61396dcbf24ba04`
- **Scope class:** documentation / research spike. **Zero product code changed.** See § 8.

---

## 0. The recommendation in one page

| | |
|---|---|
| **Recommended** | **Option 3 — extend the in-house `ImageFullscreenViewer`** |
| **Runner-up** | **Option 1 — Yet Another React Lightbox 3.32.0 + Zoom plugin (+ Thumbnails plugin)** |
| **Eliminated** | **Option 2 — PhotoSwipe 5.4.4**, on the I-1 hard gate (§ 4) |
| **Confidence** | Criteria 1–3 measured/verified at `513f4bd`. Criterion 4 (physical Android gesture quality) **not collected** — § 7. |

**Why.** The load-bearing constraint is not bundle size and not feature count. It is that `/share/$token` does not hand the viewer image *URLs* — it hands it a React *component* (`AnonymousImage`, `$token.tsx:120`) that resolves `credentials:"omit"` blob object-URLs through `acquireShareBlob`/`releaseShareBlob` and an `IntersectionObserver`-gated variant (`LazyAnonymousImage`, `$token.tsx:174`) for strip thumbs. PhotoSwipe 5 has no React render hook and no thumbnail strip at all, so it cannot host either renderer without rewriting the auth boundary that § 5 of the story marks **Never**. YARL *can* host both natively — but because our slides then become YARL *custom* slide types carrying no intrinsic image dimensions, YARL's Zoom plugin loses the input it derives zoom limits from, so the very capability we would adopt YARL for arrives degraded and needs a viewer-contract change to repair (§ 4, I-1 note; § 9 reversal trigger R2). Against that, option 3 costs an estimated **+3.7–5.3 kB raw / +1.5–2.1 kB gzip** of first-party source in an *already code-split* chunk, keeps all three test surfaces intact by construction, keeps three Codex-hardened gesture rounds instead of discarding them, and keeps the Story 48.1 geometry invariants verbatim rather than re-proving them against a vendor-owned positioning layer.

**Criterion weighting (recorded so a reader can disagree with the weights, not reverse-engineer them):**

| Criterion | Weight | Rationale |
|---|---|---|
| **I-1 — `renderImage`/`renderThumb` expressibility** | **HARD GATE.** Failing it eliminates on correctness, not score. | Breaking it breaks NFR10-SHARE-SECURITY-1 (`credentials:"omit"`) **and** the 60 req/min `(token, IP)` rate-limit mitigation (Init 12 Story 19.1) simultaneously. |
| Integration cost I-2…I-4 | High | Countable: forks avoided, testids re-attached, suites rewritten, baselines regenerated. |
| Accessibility delta | High | FR26-VIEW-1 and NFR26-A11Y-1 both name it; two live gaps already open. |
| Physical Android gesture quality | High — **but uncollected** | Why the verdict is PROVISIONAL. |
| **Bundle-size delta** | **Tiebreaker, not a gate** | The app already ships a code-split Three.js stack: `measureReducer-*.js` is **971,369 B raw / 266,484 B gzip** at baseline. A ~48 kB lazy-chunk delta cannot decide this on its own. |

---

## 1. Options scored — exactly three

Per `epics.md:4571` and `architecture.md:3369`, **exactly three** options are in scope. Resolved versions actually measured, read from the installed `node_modules/<pkg>/package.json` in the throwaway worktrees:

| # | Option | Resolved version measured | License / model |
|---|---|---|---|
| 1 | Yet Another React Lightbox + Zoom plugin | **`yet-another-react-lightbox@3.32.0`** (`"version": "3.32.0"`) | React component library; Zoom + Thumbnails ship as in-package plugins |
| 2 | PhotoSwipe 5.4.x | **`photoswipe@5.4.4`** (`"version": "5.4.4"`) — matches the epic's `5.4.x` pin | Vanilla JS; renders outside the React tree |
| 3 | Extend the in-house `ImageFullscreenViewer` | n/a — first-party, 405 LOC + 68 types + 20 barrel (`wc -l`, re-measured this run) | `@radix-ui/react-dialog ^1.1.2`, already a direct dependency paid for app-wide via `ui/dialog.tsx` |

**No fourth option was scored.** `yet-another-react-lightbox-lite` is a separate package and would constitute a fourth option, which `epics.md:4571` and `architecture.md:3369` both forbid; it was therefore **excluded by rule and not evaluated**. Recorded here per § 5 of the story so the controller can see the exclusion was deliberate rather than an oversight.

**Within-option-1 variant, surfaced per § 5.** The story's D-2 names *"the lightbox + the Zoom plugin"*. Obligations I-1 (a caller-supplied **thumb** renderer) and I-4 (the `image-viewer-strip` / `image-viewer-thumb` testids) cannot be satisfied by that pair alone — YARL's `render.thumbnail` hook lives in its **Thumbnails plugin**. Both configurations were therefore measured and both are reported below. This is a plugin of option 1, not a fourth option. **The `+ Thumbnails` figure is the one a real integration pays.**

---

## 2. Criterion 1 — measured bundle-size delta (AC-2)

### 2.1 Method

Per D-2. Every number below came from a build in this repo, under this repo's actual Vite 6 / Rollup config. **No number is sourced from a package registry, a README, or bundlephobia.**

Commands, all run from `apps/web/`:

| Step | Command | Exit |
|---|---|---|
| Baseline | `npm run build` (at `513f4bd`, main checkout) | `0` |
| Byte capture | `for f in dist/assets/*.js dist/assets/*.css; do stat -c%s "$f"; gzip -9 -c "$f" \| wc -c; done` | `0` |
| Probe worktrees | `git worktree add --detach /tmp/e53-yarl 513f4bd…` · `git worktree add --detach /tmp/e53-psw 513f4bd…` | `0` |
| Install | `npm ci --no-audit --no-fund` in each | `0` |
| Option 1 | `npm i yet-another-react-lightbox@3.32.0 --no-audit --no-fund` | `0` |
| Option 2 | `npm i photoswipe@5.4.4 --no-audit --no-fund` | `0` |
| Probe builds | `npm run build` in each worktree (3 builds: YARL+Zoom, YARL+Zoom+Thumbnails, PhotoSwipe) | `0`, `0`, `0` |
| Teardown | `git worktree remove --force /tmp/e53-yarl` · `… /tmp/e53-psw` · `git worktree prune` | `0` |

**The probe.** In each worktree the candidate's real API surface was imported **from `ImageFullscreenViewer.tsx` itself** — i.e. from the module that already forms the lazy viewer chunk (`imageViewer/index.ts:18-20`) — and parked in a `globalThis` sink so Rollup could not tree-shake it away:

```tsx
// option 1 (base)                                  // option 1 (+ Thumbnails variant) adds:
import Lightbox from "yet-another-react-lightbox";  //   .../plugins/thumbnails
import Zoom from ".../plugins/zoom";                //   .../plugins/thumbnails.css
import ".../styles.css";
(globalThis as unknown as Record<string, unknown>).__e53Probe = [Lightbox, Zoom];

// option 2 — the vendor's documented `pswpModule` integration shape
import PhotoSwipeLightbox from "photoswipe/lightbox";
import "photoswipe/style.css";
(globalThis as …).__e53Probe = [PhotoSwipeLightbox, () => import("photoswipe")];
```

### 2.2 Baseline at `513f4bd`

| Emitted asset | raw B | gzip B |
|---|---:|---:|
| `assets/index-BTtCNFg4.js` — **main bundle** | 1,159,763 | 330,947 |
| `assets/measureReducer-BRIQQypQ.js` | 971,369 | 266,484 |
| `assets/parseStl.worker-C9CNTzuk.js` | 88,432 | 26,257 |
| `assets/Viewer3DModal-BMy1dyEP.js` | 9,481 | 3,700 |
| `assets/Viewer3DInline-DuRXDj1Q.js` | 7,338 | 2,952 |
| **`assets/ImageFullscreenViewer-BdSILgDq.js` — the lazy viewer chunk** | **4,933** | **2,003** |
| `assets/weldMesh.worker-8KrXd8x8.js` | 4,463 | 1,862 |
| `assets/index-CW6qCeq6.css` — **the single app stylesheet** | 83,482 | 13,557 |
| **Totals** | **JS 2,245,779 · CSS 83,482** | **JS 634,205 · CSS 13,557** |

The lazy viewer chunk is identified **by emitted name and by the fact that it is the only chunk whose bytes move when the probe is added to `ImageFullscreenViewer.tsx`** — not assumed. There is **no viewer CSS chunk at baseline**: the shipped viewer is Tailwind-only, so all its styling already lives in the single `index-*.css`.

### 2.3 Deltas — per chunk, JS and CSS separately

**Option 1a — YARL 3.32.0 + Zoom** (`npm run build` → rc 0)

| Asset | baseline | with option 1a | Δ raw | Δ gzip |
|---|---:|---:|---:|---:|
| **lazy viewer chunk** `ImageFullscreenViewer-D2MgNz1r.js` | 4,933 / 2,003 | 46,533 / 16,832 | **+41,600** | **+14,829** |
| **NEW viewer CSS chunk** `ImageFullscreenViewer-DUzlPUW4.css` | — | 5,611 / 1,494 | **+5,611** | **+1,494** |
| main bundle `index-Dlp0rkBe.js` | 1,159,763 / 330,947 | 1,159,870 / 330,995 | +107 | +48 |
| app stylesheet `index-CW6qCeq6.css` | 83,482 / 13,557 | 83,482 / 13,557 | 0 | 0 |
| **JS total** | 2,245,779 | 2,287,486 | **+41,707** | — |
| **CSS total** | 83,482 | 89,093 | **+5,611** | — |

**Option 1b — YARL 3.32.0 + Zoom + Thumbnails** *(the configuration I-1 and I-4 actually require)* (`npm run build` → rc 0)

| Asset | baseline | with option 1b | Δ raw | Δ gzip |
|---|---:|---:|---:|---:|
| **lazy viewer chunk** `ImageFullscreenViewer-C5PampiP.js` | 4,933 / 2,003 | 53,205 / 19,072 | **+48,272** | **+17,069** |
| **NEW viewer CSS chunk** `ImageFullscreenViewer-D3afDskf.css` | — | 9,606 / 2,050 | **+9,606** | **+2,050** |
| main bundle `index-C1Qs3xVl.js` | 1,159,763 / 330,947 | 1,159,870 / 330,989 | +107 | +42 |
| app stylesheet | 83,482 / 13,557 | 83,482 / 13,557 | 0 | 0 |

**Option 2 — PhotoSwipe 5.4.4** (`npm run build` → rc 0)

| Asset | baseline | with option 2 | Δ raw | Δ gzip |
|---|---:|---:|---:|---:|
| **lazy viewer chunk** `ImageFullscreenViewer-BN_f80UI.js` (PhotoSwipe **lightbox**) | 4,933 / 2,003 | 19,993 / 6,506 | **+15,060** | **+4,503** |
| **NEW async chunk** `photoswipe.esm-Bg3rb6Hr.js` (PhotoSwipe **core**, via `pswpModule`) | — | 60,840 / 17,570 | **+60,840** | **+17,570** |
| **NEW viewer CSS chunk** `ImageFullscreenViewer-BS3PQr_k.css` (required `photoswipe.css`) | — | 4,426 / 1,468 | **+4,426** | **+1,468** |
| main bundle `index-3TaKm0xs.js` | 1,159,763 / 330,947 | 1,159,879 / 330,998 | +116 | +51 |
| app stylesheet | 83,482 / 13,557 | 83,482 / 13,557 | 0 | 0 |
| **JS combined (lightbox + core)** | — | — | **+75,900** | **+22,073** |
| **JS total** | 2,245,779 | 2,321,795 | **+76,016** | — |
| **CSS total** | 83,482 | 87,908 | **+4,426** | — |

**Option 3 — extend in-house**

**Dependency delta = 0 bytes.** `@radix-ui/react-dialog ^1.1.2` is already a direct dependency and is paid for **app-wide** — every dialog in the app routes through `ui/dialog.tsx` — so option 3 adds **no new vendor bytes to any chunk and no new supply-chain surface**.

Its cost is first-party source added to the **already-split** viewer chunk. Reported as an **ESTIMATE**, per D-2 step 3; no throwaway zoom code was written, so no false-precision number is manufactured.

*Derivation.* 53.2's feature list (`epics.md:4575`) minus what already ships, sized against the 405-line component:

| 53.2 obligation | already shipped? | est. added LOC |
|---|---|---:|
| transform state + zoom/pan clamp + reset math | no | 90–130 |
| pinch + pan + double-tap pointer handling, merged with the existing `stripOrigin`/`thumbOrigin` swipe guards (`:145-216`) | swipe/tap only | 120–160 |
| visible Zoom In / Zoom Out / Reset toolbar outside the transform layer | none exist | 50–70 |
| body scroll lock with restoration | no | 25–40 |
| safe-area / dynamic-viewport refit + rotation | partial (`dvh`, `:260`) | 20–35 |
| focus trap · Escape · return focus | **yes**, via Radix | 0 |
| **Total added** | | **305–435** |

The denominator is the source that actually **emits into this chunk**, which is `ImageFullscreenViewer.tsx` **alone — 405 lines**. `types.ts` (68 lines) is type-only and emits ~0 bytes once types are stripped, and `index.ts` (20 lines) is the lazy barrel, whose own bytes land in the **main** bundle rather than in the lazy chunk — so the combined 493 (`405 + 68 + 20`) overstates the emitting surface and flatters this option. Those **405** lines compile to 4,933 raw / 2,003 gzip in that chunk ⇒ ≈**12.2** raw B and ≈**4.9** gzip B per emitting source line under this repo's build. Applied to 305–435 added lines:

> **Option 3 estimated cost: ≈ +3.7 to +5.3 kB raw · ≈ +1.5 to +2.1 kB gzip, entirely inside the existing lazy viewer chunk. New CSS: 0 bytes (Tailwind, already in `index-*.css`). ESTIMATE, not a measurement.**

### 2.4 Which chunk absorbed the delta — and two honest caveats

**Every option's delta lands in the lazy viewer chunk, not the main bundle.** Main-bundle movement is +107 B (option 1) and +116 B (option 2) raw — the CSS-preload href strings the loader gains, nothing more. Reporting only a total would be a category error here; the numbers above are per chunk.

1. **Gzip noise on untouched chunks.** Chunks whose raw byte counts are identical across builds can still differ by 1–3 gzip bytes, because the embedded `//# sourceMappingURL=` comment carries a build-dependent hash of the same length. Per-chunk deltas on the *changed* chunks are the signal; the whole-bundle gzip totals carry a few bytes of this noise.
2. **Option 2's cost is real but arrives on a third hop.** The PhotoSwipe core is a *separate async chunk*, so the viewer-open path becomes barrel → lightbox chunk → core chunk + CSS chunk. Deferred ≠ free: any user who opens the lightbox pays all 75,900 raw bytes. It is reported split because that is what the build emits, and summed because that is what a user downloads.

### 2.5 Bundle-size ranking (tiebreaker only)

| Rank | Option | Δ JS raw | Δ JS gzip | Δ CSS raw | Δ CSS gzip |
|---|---|---:|---:|---:|---:|
| 1 | **Option 3** (estimate) | **≈ +3,700 … +5,300** | **≈ +1,500 … +2,100** | **0** | **0** |
| 2 | Option 1a (Zoom only — insufficient for I-1/I-4) | +41,600 | +14,829 | +5,611 | +1,494 |
| 3 | **Option 1b** (Zoom + Thumbnails — the real figure) | **+48,272** | **+17,069** | **+9,606** | **+2,050** |
| 4 | Option 2 | +75,900 | +22,073 | +4,426 | +1,468 |

---

## 3. The obligations being scored (D-3), restated with anchors

| # | Obligation | Anchor at `513f4bd` |
|---|---|---|
| **I-1** | Accept a **caller-supplied renderer** for the main image **and** a separate one for strip thumbnails. | `types.ts:23-27` (`ImageRenderer`), `:62-67` (props); `$token.tsx:377` `renderImage={AnonymousImage}`, `:385` `renderThumb={LazyAnonymousImage}`; `ModelGallery.tsx:213` (plain `<img>` renderer) |
| **I-2** | Stay **one component with two mounts** — no `/catalog` vs `/share` fork. | `ImageFullscreenViewer.tsx:1-3`, `:24-25` |
| **I-3** | Keep the viewer **code-split behind the existing lazy barrel** with `Suspense fallback={null}`. | `imageViewer/index.ts:18-20`; `ModelGallery.tsx:207-208`; `$token.tsx:371-372` |
| **I-4** | Keep all **three** test surfaces satisfiable. | `image-viewer-containment.spec.ts` (8 testids); `catalog-detail.spec.ts:55`; `ImageFullscreenViewer.test.tsx` (138 lines) |

The eight `image-viewer-*` testids the standing containment suite queries, with both anchors:

| testid | defined at | queried at |
|---|---|---|
| `image-viewer-root` | `ImageFullscreenViewer.tsx:268` | `image-viewer-containment.spec.ts:134` |
| `image-viewer-frame` | `:281` | `:140` |
| `image-viewer-close` | `:320` | `:202` |
| `image-viewer-strip` | `:356` | `:209` |
| `image-viewer-counter` | `:308` | `:210` |
| `image-viewer-prev` | `:332` | `:211` |
| `image-viewer-next` | `:341` | `:212` |
| `image-viewer-thumb` | `:377` | `:213` |

`data-thumb-idx` (`:378`) is **not** in this list: it is a component-internal gesture hook consumed at `:175`, and no test queries it.

---

## 4. Criterion 2 — integration cost, scored native / adapter / blocked (AC-3)

**The `renderImage` / `renderThumb` auth boundaries are described and priced below. They are not modified. This story changed no code** (§ 8).

| | **Option 1 — YARL 3.32.0** | **Option 2 — PhotoSwipe 5.4.4** | **Option 3 — in-house** |
|---|---|---|---|
| **I-1 · HARD GATE** | **native** (with Thumbnails plugin) — `render.slide?: RenderFunction<RenderSlideProps>` (`dist/types.d.ts:338`) takes a caller-supplied **React element** for the main image, and `render.thumbnail?: RenderFunction<RenderThumbnailProps>` (`dist/plugins/thumbnails/index.d.ts:47`) takes a separate one for thumbs. `AnonymousImage` and `LazyAnonymousImage` mount **unchanged**, keeping their `useEffect` acquire/release lifecycle and the `IntersectionObserver` gate. ⚠️ **See the degradation note below.** | **blocked** — PhotoSwipe 5's slide contract is `src` (URL string), `html?: string` (HTML **string**), `element?: HTMLElement` (the *page* thumbnail used for the open animation) — `dist/types/slide/slide.d.ts:5-49`. **There is no React render hook.** A React component with a blob acquire/release lifecycle cannot be mounted in a slide. Additionally the registered UI elements are exactly `arrowPrev, arrowNext, close, counter, preloader, zoom, zoomTo, panGesture` — **no thumbnail strip exists**, so `renderThumb` has no host and the rate-limit mitigation has no home. | **native by construction** — this *is* the contract (`types.ts:62-67`). Zero adaptation, zero risk to NFR10-SHARE-SECURITY-1. |
| **I-2** | **native** — a React component; one wrapper keeps both mounts prop-injected. | **adapter, with fork risk** — vanilla JS driven imperatively (`new PhotoSwipeLightbox(...).init()`) from outside the React tree. A wrapper is writable, but the two mounts would diverge on *content-source strategy* (URL vs pre-resolved blob), which is exactly the fork `:24-25` forbids. | **native** — unchanged. |
| **I-3** | **native — measured.** All YARL JS **and** its CSS landed in the lazy viewer chunk + a new sibling CSS chunk; the main bundle moved +107 B raw (§ 2.3). No module-scope side effect defeated the split. | **native — measured.** Main bundle +116 B raw; core splits into its own async chunk. Note the extra network hop (§ 2.4). | **native** — unchanged; `index.ts:18-20` untouched. |
| **I-4** | **adapter — 8 re-attachments.** YARL owns its DOM. ~6 testids are reachable through render hooks (`buttonPrev`/`buttonNext`/`buttonClose`/`buttonZoom`/`slide`/`thumbnail`); `image-viewer-root` and `image-viewer-strip` are container-level and need YARL's `className`/`styles` slots or a DOM wrapper. The **138-line unit suite is rewritten**, not extended. All **four** `catalog-detail-image-viewer-open-*` baselines regenerate. | **adapter — highest cost.** Renders into `document.body`, outside the React tree: the jsdom-based 138-line suite is largely inexpressible without a new harness. `image-viewer-strip` / `image-viewer-thumb` have **no host at all** until a custom strip is built first-party — so the "adopt a library" saving is partly refunded. All four baselines regenerate. | **native — 0 re-attachments.** All eight testids, the containment suite and the 138-line unit suite survive by construction (extended, not rewritten). ⚠️ Baselines still regenerate — see the honest note below. |

### 4.1 Verdict on the hard gate

Per D-5, an option **blocked** on I-1 is *eliminated on correctness, not merely down-scored*, because failing it breaks NFR10-SHARE-SECURITY-1 and the Init 12 Story 19.1 rate-limit mitigation simultaneously.

> **Option 2 (PhotoSwipe 5.4.4) is ELIMINATED.**

**Stated precisely, so the call can be disagreed with.** PhotoSwipe is blocked *for the shipped renderers as written*. A theoretical escape exists: mount a nested React root into slide DOM via a `contentLoad`/`contentAppend` filter and hand-write a blob-release bridge to PhotoSwipe's slide-destroy lifecycle. That escape is not scored as "adapter" because it **modifies the `renderImage` / `AnonymousImage` / `shareBlobCache` path**, which § 5 of the story marks **Never** (carried verbatim from `spec-e48-1:20` as an `Always:` constraint) — and it puts the credential-omission guarantee on a hand-written lifecycle bridge instead of React's. **This is the single sentence in this artifact most worth an operator's disagreement**; if the operator rules that hoisting blob resolution out of the viewer is acceptable, I-1 is re-scored and option 2 returns (reversal trigger R4, § 9).

### 4.2 ⚠️ Option 1's degradation note — YARL Zoom over custom slides

YARL's Zoom plugin derives its maximum zoom level from the **intrinsic pixel dimensions of a YARL image slide**. Once `render.slide` returns our own React element, the slide is a **custom slide type**, and the plugin's own typings acknowledge this with dedicated escape hatches — `zoom.supports?: readonly SlideTypeKey[]` ("custom slide types that support zoom") and `zoom.maxZoom?: number | ((slide) => number | undefined)` ("maximum zoom level for custom slide types; … default: 8") (`dist/plugins/zoom/index.d.ts`).

Our `ImageSource` contract is `{ fullUrl, thumbUrl, alt }` (`types.ts:35-39`) — **it carries no width or height**. So on the configuration I-1 forces us into, YARL's zoom falls back to a flat default rather than per-image limits. Repairing it means widening `ImageSource` with pixel dimensions and plumbing them from both mounts' DTOs — a viewer-contract change, plus a data-availability question this story did not resolve.

**This is the crux of the recommendation:** the capability we would adopt YARL *for* is precisely the capability that arrives degraded once the auth boundary is honoured, and the vendor demos (§ 7) will **not** show that degradation because they feed YARL plain image URLs.

### 4.3 ⚠️ Correction to the story's baseline count (I-4)

The story's I-4 asks whether *"the two `catalog-detail` mobile baselines"* must be regenerated. Measured this run:

```
apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/
  catalog-detail-image-viewer-open-desktop-dark.png
  catalog-detail-image-viewer-open-desktop-light.png
  catalog-detail-image-viewer-open-mobile-dark.png
  catalog-detail-image-viewer-open-mobile-light.png
```

**Four** baselines exist, not two — `catalog-detail.spec.ts:55` asserts one screenshot name across the fixed 4-project matrix. Story 48.1 regenerated only the **two mobile** ones because its change was sub-pixel on desktop. **Any option that replaces the viewer's DOM regenerates all four**, each needing a `baseline-reviewed:` sign-off line under the Baseline Acceptance Gate.

**And an honesty note that cuts against the recommendation:** option 3 does **not** earn free baselines either. 53.2 adds a visible zoom toolbar in *every* option, so all four `catalog-detail-image-viewer-open-*` PNGs regenerate regardless of which option wins. What option 3 uniquely preserves is the **geometry containment suite** (`image-viewer-containment.spec.ts` — bounding-box assertions, no snapshots), which stays green with **zero edits**, and the 138-line unit suite, which extends rather than being rewritten.

---

## 5. Criterion 3 — accessibility, scored as a delta from the shipped Radix baseline (AC-4)

### 5.1 The baseline this is a delta *from* (not from zero)

| APG / WCAG obligation | Shipped today | Anchor |
|---|---|---|
| modal-dialog semantics (`role="dialog"` + `aria-modal`) | ✅ via Radix `Dialog` / `DialogContent` | `ImageFullscreenViewer.tsx:225-226`, `@radix-ui/react-dialog ^1.1.2` |
| focus trap | ✅ Radix | same |
| return focus on close | ✅ Radix | same |
| Escape closes | ✅ Radix default (`:128-130` deliberately does not intercept) | `:225` |
| accessible name for the dialog | ✅ sr-only i18n `DialogTitle` | `:263-265` |
| accessible names for controls | ✅ `aria-label` on close / prev / next / each thumb, `aria-current` on the active thumb | `:322`, `:334`, `:343`, `:383-384` |
| chrome hidden from AT when visually hidden | ✅ `aria-hidden` follows `chromeVisible` | `:304`, `:371` |
| **≥44×44 close target** | ❌ **40×40** (`h-10 w-10`) — below what `epics.md:4579` demands | `:323` |
| **visible zoom controls (WCAG 2.2 SC 2.5.1 / 2.5.7)** | ❌ **none exist** — there is nothing to satisfy yet | `:20` marks pinch-zoom DEFERRED |

Prev/next chevrons are already `h-12 w-12` = 48×48 (`:335`, `:344`) — compliant.

**Both live gaps are recorded here as Story 53.2 obligations. Neither is fixed by this story** (§ 8).

### 5.2 Per-option delta

| | **Option 1 — YARL 3.32.0** | **Option 2 — PhotoSwipe 5.4.4** | **Option 3 — in-house** |
|---|---|---|---|
| APG modal-dialog semantics | **native** — verified in `dist/index.js`: `role: "dialog"`, `"aria-modal": true`, `tabIndex: -1` on the container | **native** — `trapFocus: true` and `escKey: true` are shipped defaults in `dist/photoswipe.esm.js` | **already shipped** via Radix — no delta, no work |
| focus trap | vendor-implemented; **must be re-verified in 53.2** — this story read the ARIA attributes out of the installed package, it did **not** exercise the trap behaviour | vendor-implemented; **must be re-verified in 53.2** — `trapFocus: true` is a **documented default read from the installed `dist/photoswipe.esm.js`**; the trap behaviour was **not** exercised | ✅ already green |
| return focus | vendor-implemented; re-verify in 53.2 | vendor-implemented; re-verify in 53.2 — `returnFocus: true` is a **documented default read from the installed package**; the return-focus behaviour was **not** exercised | ✅ already green |
| control accessible names / **i18n** | **native, i18next-injectable** — `aria-label` is sourced from `buttonLabel` / `translateLabel`, both driven by the `labels` prop | **adapter** — shipped titles are English literals (`'Close'`, `'Next'`, `'Previous'`, `'Zoom'`), overridable via the `closeTitle` / `zoomTitle` / `arrowPrevTitle` / `arrowNextTitle` options (all verified present). But the root renders **outside the React tree**, so i18next values must be pushed in imperatively at init and re-pushed on language change | **already shipped** — `t()` everywhere; new controls just add keys to `en.json` + `pl.json` |
| **visible zoom controls, no pinch required** | **native, partial** — the Zoom plugin registers **Zoom In and Zoom Out toolbar buttons by default** (`ZoomInIcon`, `ZoomOutIcon`, `buttonZoom` in `dist/plugins/zoom/index.js`; labels `"Zoom in"` / `"Zoom out"`). **No Reset button** — 53.2 must add one via `render.buttonZoom` | **partial** — exactly **one** `zoom` toggle button (title `'Zoom'`), a fit↔fill toggle. Not Zoom In / Zoom Out / Reset. Gives *a* single-pointer path to zoom, but no incremental control and no explicit reset ⇒ FR26-VIEW-1 and `epics.md:4575` are **not** met without custom UI | **none by default — must be built** — all three buttons are first-party work, but with full control over labels, tokens, dark mode and placement outside the transform layer |
| **≥44×44 hit targets** | **native** — `.yarl__button{padding:8px}` + `.yarl__icon{32px}` ⇒ **48×48**; nav `padding:24px 16px` ⇒ 64×80. Closes the shipped 40×40 gap **by default** | **native** — `.pswp__button{width:50px;height:60px}` ⇒ **50×60**. Also closes the gap by default | **must be fixed by hand** — bump `h-10 w-10` → `h-11 w-11` (44) or `h-12 w-12` (48) at `:323`. One-line change, but explicitly 53.2's, not this story's |

**Summary.** On accessibility alone, **options 1 and 2 both arrive with the 40×40 gap already closed and (option 1) two of the three required zoom controls already visible** — a genuine, measured advantage over option 3, which must build all of it. Option 3's compensating advantage is that its entire a11y surface is already i18n-wired, theme-token-wired, and covered by the shipped unit suite. **No option ships a Reset control; 53.2 builds it in all three worlds.**

---

## 6. Criterion 3b — do the Story 48.1 geometry invariants survive?

`architecture.md:3371-3376` binds five invariants on whichever option wins. Restated **verbatim** in § 9.3. Scored here:

| | Option 1 — YARL | Option 2 — PhotoSwipe | Option 3 — in-house |
|---|---|---|---|
| owns its positioning layer? | **yes** — `.yarl__portal{position:fixed;top:0;right:0;bottom:0;left:0;z-index:9999}` + `.yarl__container{position:absolute;inset:0}`. The 48.1 className at `:260` is **replaced**, not inherited | **yes** — renders its own root into `document.body`; the className is replaced | **no** — `:260` is kept verbatim |
| can the 48.1 *mixed-reference-box* root cause recur? | **no, by construction** — `top/right/bottom/left:0` is a **single** reference box; there is no `left:50%`-vs-`vw` mixing. **But** a fixed inset-0 box still resolves against mobile Chrome's *layout* viewport, so the layout-vs-visual divergence 48.1 measured is **not** addressed either — it must be re-proved on device, not assumed | same reasoning; must be re-proved on device | **not applicable** — the shipped fix stays in place, and `image-viewer-containment.spec.ts` keeps proving it every run |
| override mechanism for our geometry | YARL CSS custom properties (`--yarl__*`) + its `className` / `styles` slots. **Not** the `cn`/`twMerge` override path we use against `dialog.tsx` today | CSS custom properties + `pswp__*` class overrides; no React-side hook | unchanged — `cn`/`twMerge` on our own `DialogContent` |
| `dvh` height budget | must be re-expressed against the vendor's layer | must be re-expressed against the vendor's layer | **kept verbatim** (`:260`, `:294`) |
| `user-scalable=no` | not proposed by any option; **none of the three write-ups propose it** | same | same |
| body scroll lock with restoration (FR26-VIEW-1) | **native** — `.yarl__no_scroll{height:100%;overflow:hidden;overscroll-behavior:none}` | native (`pswp` locks scroll) | **must be built** — 25–40 LOC (§ 2.3) |

**Gesture-model note.** `.yarl__container` sets `touch-action: var(--yarl__controller_touch_action, none)` — YARL takes ownership of the whole touch surface. Adopting it therefore **discards the three Codex-hardened rounds** behind the shipped gesture layer (22.3 r3, 28.2, 28.2 r3 — the coords-based `stripOrigin` guard at `:148-163`, the narrow `thumbOrigin` deferral at `:164-176`, and the hidden-strip pass-through at `:206-211`) and re-earns that hardening against a different gesture model. `epics.md:4575` requires *"explicit swipe-vs-pan conflict rules"* — in options 1 and 2 those rules must be negotiated with the vendor's controller; in option 3 they extend rules that are already tuned and regression-covered.

---

## 7. Criterion 4 — physical Android Chrome protocol (AC-5) · **RESULTS NOT COLLECTED**

> **The dev agent has no physical Android device.** `epics.md:4579` forbids simulating or inferring this evidence: *"final gesture acceptance requires a physical Android Chrome smoke, recorded as operator evidence and never simulated or inferred."* **No gesture-quality claim anywhere in this artifact is asserted, simulated, or inferred from library documentation.** The result cells below are deliberately blank.

**Zero code. Zero deploy.** All three options are already reachable from a phone today.

### 7.1 Setup — one device, one browser, one session

| | |
|---|---|
| Device | Physical Android phone (record model + Android version) |
| Browser | Chrome for Android (record version) |
| Session | All three URLs in **one** session, same orientation sequence, same lighting, back to back |
| Do **not** | use an emulator, Chrome DevTools device mode, or a desktop touchscreen |

| Option | URL to open |
|---|---|
| **1 — YARL 3.32.0 + Zoom** | `https://yet-another-react-lightbox.com` → the **Zoom plugin** demo |
| **2 — PhotoSwipe 5.4.4** | `https://photoswipe.com` → the vendor demo gallery |
| **3 — in-house viewer** | `https://3d.ezop.ddns.net` → any `/catalog/<id>` with photos → tap a photo to open fullscreen (**this is the deployed Story 48.1 code**) |

### 7.2 ⚠️ Stated confounder

The vendor demo pages **do not run this repo's image pipeline or auth**. **Gesture feel transfers; load behaviour does not.** Do not read a demo's fast image swap as evidence about our blob-resolved `/share/$token` path — and note that the demos feed the libraries plain image URLs, i.e. exactly the configuration § 4.2 shows we cannot use.

**For option 3, be explicit about what is being judged:** the in-house viewer today has **no pinch, no pan, no double-tap and no zoom controls** (`ImageFullscreenViewer.tsx:20-21`). What criterion 4 asks of option 3 is the quality of the **existing swipe/tap layer** and **toolbar/close reachability** — not a zoom comparison. Scoring option 3 low for "no pinch" would be scoring the question 53.2 exists to answer.

### 7.3 Ordered gesture checklist — run in this order for each option

| # | Gesture / check | Opt 1 (YARL) | Opt 2 (PhotoSwipe) | Opt 3 (in-house) |
|---|---|---|---|---|
| G1 | Open fullscreen from a thumbnail — does it feel immediate? | ␣ *not collected* | ␣ *not collected* | ␣ *not collected* |
| G2 | Swipe left / right to the next & previous image — does it track the finger? | ␣ | ␣ | ␣ |
| G3 | Pinch to zoom in — smooth, or stepped/laggy? *(n/a for opt 3 today — record "n/a, deferred")* | ␣ | ␣ | ␣ |
| G4 | Pan while zoomed — does it follow the finger and clamp at the edges? *(n/a for opt 3)* | ␣ | ␣ | ␣ |
| G5 | Double-tap to zoom in, double-tap to reset *(n/a for opt 3)* | ␣ | ␣ | ␣ |
| G6 | While zoomed, swipe horizontally — does it **pan** or **navigate**? (the swipe-vs-pan conflict) | ␣ | ␣ | ␣ |
| G7 | Tap the visible **Zoom In / Zoom Out** controls — reachable one-handed? *(opt 3: none exist — record "none")* | ␣ | ␣ | ␣ |
| G8 | Is there a visible **Reset** control? | ␣ | ␣ | ␣ |
| G9 | Close button — reachable with the thumb, comfortably hit on the first try? | ␣ | ␣ | ␣ |
| G10 | Scroll the thumbnail strip — does it scroll without triggering image navigation? *(opt 2: no strip exists — record "none")* | ␣ | ␣ | ␣ |
| G11 | Rotate to landscape and back — does the image refit without clipping? | ␣ | ␣ | ␣ |
| G12 | With the Chrome toolbar showing, is any control cut off at the bottom or right edge? | ␣ | ␣ | ␣ |
| G13 | Browser pinch-zoom of the *page* still works (i.e. nothing behaves like `user-scalable=no`)? | ␣ | ␣ | ␣ |
| G14 | Close, then reopen — does focus return sensibly and does scroll position restore? | ␣ | ␣ | ␣ |

**Recording fields (fill on collection):** device model · Android version · Chrome version · date · per-row verdict (`good` / `acceptable` / `poor` / `n/a`) · free-text notes for anything surprising.

### 7.4 Consequence

Because § 7.3 is uncollected, **this recommendation is PROVISIONAL — pending physical Android Chrome evidence**, and **G26-LIB is not closed by this story**. The artifact is written to accept the results as a later amendment to § 7.3 and § 9.2 **without a rewrite**.

#### 7.4a Amendment 2026-08-02 — partial/coarse physical evidence now exists; **the verdict does not move**

> Added by the E53 / `G26-LIB` status reconciliation (native `bmad-correct-course` route). **Repo-local Claude Opus 5, NOT an Ezop signature, NOT human review.** § 7.3's cells stay blank — this amendment fills none of them.

Physical evidence on a **Pixel 9 Pro / Android 17**, against the deployed Story 53.4 repair (commit `e76e94f`, release `0.1.0+e76e94f`), now exists in two pieces — and **both are partial**:

- **Chrome for Android 150.0.7871.186 — COARSE only.** The operator reports the surface *"works broadly"* with **no per-row verdict**. Recorded as a dated free-text note in `53-3-lightbox-test-contract.md` § 11.2a; `G0`–`G14` there remain **uncollected**.
- **Brave — detailed, but the WRONG BROWSER for this section.** Zoomed drag pans rather than navigates; Reset restores swipe navigation; thumb-strip scroll does not navigate; portrait → landscape → portrait survives; close/reopen restores page state; fit/scaling/gestures acceptable, portrait works, and the operator explicitly does not want polish time spent now. Recorded in `53-4-android-chromium-lightbox-fit-repair.md` § 9 (R-8 `NOT PERFORMED`). **§ 7 asks a Chrome question; Brave answers do not migrate into it.**

**No § 9.2 reversal trigger fired, checked one by one and stated rather than asserted:**

| | Status against the 2026-08-02 evidence |
|---|---|
| **R1** — the shipped swipe/tap/close layer is *poor* on device (`G2`, `G9`, `G10`, `G12`, `G14`) | **NOT fired.** Nothing reported is negative. What *was* reported on those subjects (thumb-strip scroll does not navigate; close/reopen restores page state) is **favourable and on Brave**, and no `G2`/`G9`/`G12` observation exists at all. |
| **R2** — YARL zoom decisively better on device **AND** per-image pixel dimensions cheaply available to both DTOs | **NOT fired.** Neither conjunct is touched: no comparative option run was performed (§ 7.3 needs all three options on one device), and no DTO work happened. |
| **R3** — the in-house transform/clamp layer exceeds ≈450 added LOC or needs a gesture-math dependency | **NOT fired.** Settled inside Story 53.2 and unaffected by field evidence; Story 53.4 added **zero** dependencies. |
| **R4** — the operator rules that hoisting blob resolution out of the viewer is acceptable | **NOT fired.** No such ruling was given. |
| **R5** — a11y review rules that shipping without visible zoom controls is unacceptable | **NOT fired**, and the evidence points the other way: the shipped viewer's zoom/reset controls are visible and were used on device (Brave `R-5`/`R-6`). The operator's one a11y-adjacent remark — that tapping the image intentionally leaves those controls visible — is **treated as non-blocking** and ledgered, not raised as a defect. |

**Therefore: the § 0 / § 9.1 call is UNCHANGED (option 3 — extend the in-house viewer), the verdict stays 🟡 PROVISIONAL, and `G26-LIB` stays 🔓 OPEN.** What would move any of this is a **collected** § 7.3 / § 11.2 run on Chrome for Android, or an explicit **controller** ruling that the coarse evidence is sufficient. Neither has happened.

---

## 8. Zero product code — the proof (AC-6)

**What this proof is measured against, and why not `513f4bd..HEAD`.** Nothing is committed on `docs/E53.1-lightbox-adoption-spike` yet — the branch tip *is* `513f4bd`, so `git diff --stat 513f4bd..HEAD` is an **empty range** and would print nothing no matter what the tree contained. An empty range diff proves nothing about scope confinement, and it is **not** the evidence for AC-6. The evidence below is the **working tree measured against the baseline commit**, plus a full untracked-file enumeration, which is what actually constrains what a subsequent `docs:` commit can carry.

| Check | Command | Result |
|---|---|---|
| Tracked changes vs baseline confined to `_bmad-output/**` | `git diff --name-only 513f4bd` (working tree vs baseline) | ✅ exactly 4 paths: `53-1-lightbox-adoption-spike.md`, this artifact, `sprint-status.yaml`, `triage-backlog.md` |
| Nothing else pending anywhere in the tree | `git status --porcelain` | ✅ exactly 4 lines, all `_bmad-output/implementation-artifacts/` + `_bmad-output/triage-backlog.md` |
| No stray untracked leftovers (probe output, `node_modules`, logs) | `git ls-files --others --exclude-standard` | ✅ **0 lines** |
| No `apps/` `workers/` `infra/` modification | `git status --porcelain -- apps workers infra \| wc -l` | ✅ **0** (exact line count, not a visual scan) |
| `apps/web/package.json` byte-identical | `git diff --exit-code 513f4bd -- apps/web/package.json apps/web/package-lock.json` | ✅ rc **0** |
| `apps/web/package.json` content identity | `sha256sum apps/web/package.json` vs `git show 513f4bd:apps/web/package.json \| sha256sum` | ✅ both `b620e2f1afce0ce7ad74ef1764cd80672541814ed1dfe837a374efd7597e8e72` |
| `apps/web/package-lock.json` content identity | `sha256sum apps/web/package-lock.json` vs `git show 513f4bd:apps/web/package-lock.json \| sha256sum` | ✅ both `aa82670c88ae0f3dc37f3c4bb60549ab3c046520703f9720f82108b430e18d95` |
| Every throwaway worktree removed | `git worktree list` | ✅ no E53 worktree; the only entries are the pre-existing `3d-portal-e47-5-review`, three `bmad-loop/20260722-*` run worktrees and `3d-portal-e49-5-dev`, all untouched by this story |

The probe edits to `ImageFullscreenViewer.tsx` existed **only inside the two detached throwaway worktrees**, which were removed with `git worktree remove --force`. The story branch never held them.

Once the `docs:` commit exists, `git diff --stat 513f4bd..HEAD` becomes a meaningful second check and should show the same four `_bmad-output/**` paths and nothing else. It is a **post-commit** confirmation of this proof, not a substitute for it.

---

## 9. The recommendation (AC-7)

### 9.1 Ranked call

> ## ✅ RECOMMENDED — **Option 3: extend the in-house `ImageFullscreenViewer`**
> ## 🥈 RUNNER-UP — **Option 1: YARL 3.32.0 + Zoom + Thumbnails**
> ## ❌ ELIMINATED — **Option 2: PhotoSwipe 5.4.4** (I-1 hard gate, § 4.1)
>
> ### **PROVISIONAL — pending physical Android Chrome evidence (§ 7). G26-LIB REMAINS OPEN.**

**The case for option 3, in the order the criteria are weighted:**

1. **I-1, the hard gate, is satisfied natively and at zero risk.** Option 3 *is* the `renderImage`/`renderThumb` contract. NFR10-SHARE-SECURITY-1 and the Init 12 rate-limit mitigation stay exactly where they are, protected by React's own lifecycle. Option 1 also passes I-1 — but only by making our slides YARL *custom* slide types, which is precisely what degrades its zoom (§ 4.2).
2. **Integration cost is zero where it is countable.** 0 testid re-attachments vs 8; the 138-line unit suite extends rather than being rewritten; the standing containment suite (`architecture.md:3376`) stays green with zero edits; no fork risk at either mount.
3. **Accessibility is where option 3 genuinely loses.** Options 1 and 2 arrive with ≥44×44 targets and (option 1) visible Zoom In/Out already built. Option 3 must build three buttons and widen one hit target. This is real work — but it is *bounded, one-line-to-70-line* work on a surface that is already i18n-, theme- and test-wired, and no option ships the Reset control the epic demands.
4. **Bundle size is the tiebreaker and it points the same way:** ≈+1.5–2.1 kB gzip (estimated, first-party) vs +17.1 kB gzip JS + 2.05 kB gzip CSS (measured, option 1b) vs +22.1 kB gzip JS (measured, option 2). Not decisive on its own in an app that already ships a 266 kB gzip Three.js chunk — but it is not nothing, and it is free.
5. **Decision BA's own instruction.** *"A dependency must earn its place."* On this evidence, YARL earns roughly two-thirds of a place: it brings real gesture engineering and real a11y defaults, and it takes away three rounds of hardened swipe/strip disambiguation, the 48.1 geometry expression, the unit suite, eight test handles, and — because of the custom-slide constraint — a meaningful share of the zoom quality that was the reason to adopt it.

**What would make this call wrong:** § 9.2. **What 53.2 must then build:** § 9.4.

### 9.2 Reversal triggers — the specific evidence that flips the call

| # | Trigger | Consequence |
|---|---|---|
| **R1** | The § 7 physical Android run shows option 3's **existing** swipe/tap/close layer is poor on device (G2, G9, G10, G12, G14) — i.e. the foundation is weaker than the regression suite suggests, not merely missing pinch. | The "extend a hardened layer" premise fails. **Option 1 promotes to recommended.** |
| **R2** | The § 7 run shows YARL's zoom decisively better than a plausible hand-built transform layer **AND** per-image pixel dimensions turn out to be cheaply available to both mounts' DTOs (so `ImageSource` can carry `width`/`height` and § 4.2's degradation dissolves). | **Both conditions required.** Option 1's central objection is removed. **Option 1 promotes to recommended.** |
| **R3** | 53.2 scoping shows the in-house transform/clamp layer exceeding ≈450 added LOC, or needing a third-party gesture-math dependency anyway. | The "0 dependency bytes" advantage is illusory. **Option 1 promotes to recommended.** |
| **R4** | The operator rules that hoisting blob resolution out of the viewer — i.e. changing the `renderImage` / `AnonymousImage` / `shareBlobCache` contract that § 5 marks **Never** — is acceptable. | I-1 is re-scored for option 2. **Option 2 returns to contention** (it would still rank last on bundle size and would still need a first-party thumbnail strip). |
| **R5** | A11y review rules that shipping without visible zoom controls for even one release is unacceptable, and 53.2 must land in the smallest possible number of steps. | Option 1's default Zoom In/Out toolbar becomes decisive. **Option 1 promotes to recommended.** |

Any trigger firing is a `bmad-correct-course` input, not a silent re-decision.

### 9.3 The five Story 48.1 invariants — restated verbatim, binding on whichever option wins

From `architecture.md:3371-3376`, **Carried-forward invariants from Story 48.1 (must not regress):**

> - viewport-anchored geometry expressed in **one** reference box (`left-[1vw]` + `translate-x-0`, never `left-1/2` + `-translate-x-1/2`) — the measured root cause of the shipped defect was `left: 50%` resolving against the layout viewport while `w-[98vw]` resolved against the visual viewport;
> - `dvh`, not `vh`, for the height budget (on a phone `vh` is the *large* viewport and overshoots while the browser toolbar is showing);
> - **never** suppress browser pinch-zoom via `user-scalable=no` (accessibility);
> - `apps/web/src/ui/dialog.tsx` is **Ask First** — blast radius is every dialog in the app;
> - `apps/web/tests/visual/image-viewer-containment.spec.ts` is a **standing** suite E53 keeps green, not one it replaces.

### 9.4 Handoff to Story 53.2 — conditional on which option wins

**If the recommendation stands (option 3), 53.2 must build in-house:**

1. **Transform layer** — zoom scale + pan offset state, clamped to image bounds, held **outside** the toolbar's render subtree so the toolbar is stable per `epics.md:4575`.
2. **Pinch-to-zoom, pan, double-tap-to-zoom/reset**, integrated with — not replacing — the existing `stripOrigin` / `thumbOrigin` guards at `:145-216`. The shipped `SWIPE_THRESHOLD_PX = 50` / `SWIPE_VERTICAL_TOLERANCE_PX = 60` constants (`:43-48`) are the current swipe contract; any change to them is a deliberate, justified decision, not a side effect.
3. **Explicit swipe-vs-pan conflict rules** — at zoom = 1 horizontal swipe navigates; above zoom = 1 it pans until the pan clamps at an edge. Written as an explicit rule, not emergent behaviour.
4. **Visible Zoom In / Zoom Out / Reset controls** — i18n keys in both `en.json` and `pl.json`, accessible names, ≥44×44, satisfying WCAG 2.2 SC 2.5.1 / 2.5.7 **without pinch**.
5. **Raise the close target from 40×40 to ≥44×44** (`:323`, `h-10 w-10` → `h-11 w-11` or `h-12 w-12`) — the gap recorded in § 5.1.
6. **Body scroll lock with restoration.**
7. **Safe-area + dynamic-viewport handling and rotation refit**, keeping `dvh` (`:260`, `:294`) and never introducing `user-scalable=no`.
8. **Keep all eight `image-viewer-*` testids and the containment suite green with zero edits**; extend `ImageFullscreenViewer.test.tsx` rather than rewriting it.
9. **Regenerate the four `catalog-detail-image-viewer-open-*` baselines** with a `baseline-reviewed:` sign-off line per PNG (Baseline Acceptance Gate).
10. **Do not touch** `ui/dialog.tsx` (Ask First), `renderImage`/`renderThumb`, `AnonymousImage`/`LazyAnonymousImage`/`shareBlobCache`, or `Viewer3DModal` and the other deferred `DialogContent` consumers (`architecture.md:3378`).

**If a reversal trigger fires and option 1 wins instead, 53.2 must additionally:**

1. Add `yet-another-react-lightbox@3.32.0` **plus** the Zoom **and** Thumbnails plugins — budget the measured **+48,272 B raw / +17,069 B gzip JS and +9,606 B raw / +2,050 B gzip CSS**, all in the lazy viewer chunk.
2. Wire `render.slide` → `AnonymousImage` and `render.thumbnail` → `LazyAnonymousImage` **without altering either component**, and prove `credentials:"omit"` and the `IntersectionObserver` gate still hold at `/share/$token`.
3. Resolve § 4.2: either widen `ImageSource` with pixel dimensions and plumb them from both mounts, or accept and document a flat `zoom.maxZoom` for custom slide types.
4. Re-attach all eight testids through YARL's render hooks and `className`/`styles` slots; **rewrite** the 138-line unit suite; regenerate all four baselines.
5. Re-express the 48.1 geometry against `.yarl__portal` / `.yarl__container` via `--yarl__*` custom properties and **re-prove the containment suite on device** — `architecture.md:3376` keeps that suite standing regardless of who owns the DOM.
6. Route every YARL label through i18next via the `labels` prop, and add a **Reset** control via `render.buttonZoom` (YARL ships In/Out only).

---

## 10. Provenance and limits of this artifact

- **What was measured:** three production builds in two throwaway worktrees at `513f4bd`, byte-exact raw and gzip per emitted chunk (§ 2).
- **What was read from shipped code:** every `apps/web` anchor cited here was opened this run; every line number was re-verified against the file before being written down.
- **What was read from the vendors' installed packages** (not their marketing pages): `yet-another-react-lightbox@3.32.0` — `dist/types.d.ts`, `dist/plugins/zoom/index.d.ts`, `dist/plugins/thumbnails/index.d.ts`, `dist/index.js`, `dist/styles.css`. `photoswipe@5.4.4` — `dist/types/slide/slide.d.ts`, `dist/photoswipe.esm.js`, `dist/photoswipe.css`.
- **What was NOT done:** no prototype was written (prototyping is 53.2's job); vendor focus-trap *behaviour* was not exercised, only its ARIA attributes and documented defaults were verified; **no physical device was touched**.
- **What is an estimate and labelled as one:** option 3's first-party byte cost (§ 2.3) and its 305–435 added LOC.
- **Two corrections to the story's own framing, recorded rather than silently applied:** the `catalog-detail` baseline count is **four**, not two (§ 4.3); and option 1 requires the **Thumbnails** plugin, which D-2's measurement recipe did not name — both configurations are reported (§ 2.3).
- **Gate status:** `G26-LIB` **OPEN**. This artifact is one of its two closure conditions. Recording the Decision BA outcome in `architecture.md` is explicitly **not** this story's edit — it routes through `bmad-correct-course` once the operator closes the gate.
