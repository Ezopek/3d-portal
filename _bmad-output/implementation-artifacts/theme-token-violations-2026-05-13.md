---
title: "Theme Token Violations Audit — Initiative 3 / Story 5.1"
type: audit-report
story: E5.1
date: 2026-05-13
status: complete
---

Read-only sweep of `apps/web/src/` for color literals that bypass the theme-token contract (arbitrary-bracket palette values, raw Tailwind palette utilities, raw `bg-white`/`bg-black`/`text-white`/`text-black`). Severity follows Decision C from Initiative 3 architecture: P0 under `ui/**`, P1 under `modules/**/components/`, P2 elsewhere. Suggested replacements are populated where a clear token already exists in `theme.css`; ambiguous cases are deferred to the relevant Phase B story.

| file:line | pattern matched | current literal value | suggested token replacement | severity |
|---|---|---|---|---|
| apps/web/src/ui/dialog.tsx:34 | arbitrary-bracket rgba | `bg-[rgba(0,0,0,0.15)]` | `<TBD-story-5.7>` — needs `--color-overlay-scrim` token introduction | P0 |
| apps/web/src/ui/dialog.tsx:56 | arbitrary-bracket rgba | `bg-[rgba(8,12,20,0.5)]` | `<TBD-story-5.7>` — needs `--color-dialog-surface` token introduction | P0 |
| apps/web/src/ui/sheet.tsx:29 | arbitrary-bracket rgba | `bg-[rgba(0,0,0,0.15)]` | `<TBD-story-5.7>` — share `--color-overlay-scrim` with dialog | P0 |
| apps/web/src/ui/custom/CardCarousel.tsx:158 | bg-black/text-white opacity | `bg-black/40 text-white` (+ `hover:bg-black/60`) | `<TBD-story-5.10>` — gallery-control surface token | P0 |
| apps/web/src/ui/custom/CardCarousel.tsx:167 | bg-black/text-white opacity | `bg-black/40 text-white` (+ `hover:bg-black/60`) | `<TBD-story-5.10>` — gallery-control surface token | P0 |
| apps/web/src/ui/custom/CardCarousel.tsx:186 | bg-white opacity | `bg-white` / `bg-white/40` / `hover:bg-white/70` | `<TBD-story-5.10>` — carousel dot indicator token | P0 |
| apps/web/src/modules/catalog/components/viewer3d/measure/RimOverlay.tsx:8 | raw palette + bg/text-white | `bg-zinc-900/95 ... text-white ... ring-white/15` | `bg-viewer-tooltip text-viewer-tooltip-foreground ring-viewer-tooltip-ring` `<TBD-story-5.8>` (tokens to be added) | P1 |
| apps/web/src/modules/catalog/components/viewer3d/measure/MeasureOverlay.tsx:16 | raw palette + bg/text-white | `bg-zinc-900/95 ... text-white ... ring-white/15` | `bg-viewer-tooltip text-viewer-tooltip-foreground ring-viewer-tooltip-ring` `<TBD-story-5.8>` (tokens to be added) | P1 |
| apps/web/src/modules/catalog/components/ModelGallery.tsx:93 | bg-black/text-white opacity | `bg-black/40 text-white` (+ `hover:bg-black/60`) | `<TBD-story-5.10>` — gallery-control surface token (shared w/ CardCarousel) | P1 |
| apps/web/src/modules/catalog/components/ModelGallery.tsx:102 | bg-black/text-white opacity | `bg-black/40 text-white` (+ `hover:bg-black/60`) | `<TBD-story-5.10>` — gallery-control surface token (shared w/ CardCarousel) | P1 |
| apps/web/src/modules/catalog/components/ModelGallery.tsx:106 | bg-black/text-white opacity | `bg-black/50 text-white` (image-counter badge) | `<TBD-story-5.10>` — gallery-counter badge token | P1 |

## Conclusions

**Totals by severity**
- P0 (apps/web/src/ui/**): 6 occurrences across 3 files (`dialog.tsx` ×2, `sheet.tsx` ×1, `custom/CardCarousel.tsx` ×3)
- P1 (apps/web/src/modules/**/components/): 5 occurrences across 3 files (`viewer3d/measure/RimOverlay.tsx` ×1, `viewer3d/measure/MeasureOverlay.tsx` ×1, `ModelGallery.tsx` ×3)
- P2 (elsewhere in apps/web/src/**): 0

**Seed-violation sanity check**
All 5 brief-seeded violations appear above:
- `dialog.tsx:34` — present (row 1)
- `dialog.tsx:56` — present (row 2)
- `sheet.tsx:29` — present (row 3)
- `RimOverlay.tsx:8` — present (row 7)
- `MeasureOverlay.tsx:16` — present (row 8)

**Surprises (not in the seed list)**
1. **`ui/custom/CardCarousel.tsx`** — three additional P0 violations on the same control surface (nav arrows + dot indicator). This raises the dialog/sheet "shared overlay surface" story's P0 footprint from 3 to 6 sites. Story 5.10 was already the planned bucket for bulk gallery work; recommend pulling the dot-indicator case explicitly into its scope.
2. **`modules/catalog/components/ModelGallery.tsx`** — three P1 violations (nav arrows + image-counter badge) mirroring the CardCarousel pattern. Strongly suggests a shared "image-gallery control" token pair (`--color-gallery-control` / `--color-gallery-control-foreground`) introduced in story 5.10 and reused across both files.
3. **No P2 hits** — confirms the linting + theme-token boundary is well respected outside `ui/`/`modules/**/components/`. No leak into pages, hooks, lib, tests.
4. **No `oklch(...)` / `color(...)` / `#hex` literals were found** under the heuristics. The only `oklch(...)` consumer is `palette.ts` (programmatic, intentional — viewer measurement palette). This is an enabler signal for Decision C scope: the lint rule can confidently flag `bg-[#…]`, `bg-[rgba(…)]`, `bg-[hsl(…)]`, `bg-[oklch(…)]` without producing false positives in current source.
