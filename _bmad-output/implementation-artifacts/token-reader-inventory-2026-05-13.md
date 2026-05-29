---
title: "Theme Token Reader Inventory — Initiative 3 / Story 5.1"
type: audit-report
story: E5.1
date: 2026-05-13
status: complete
---

Read-only sweep of `apps/web/src/` for code that programmatically consumes CSS theme tokens (as opposed to applying them via Tailwind `bg-*` / `text-*` utilities). This inventory exists to validate Decision K's working assumption — that only `readMeshTokens.ts` and `palette.ts` read tokens outside the browser CSS engine — which determines whether Story 5.5 (token consumer audit) can be a single-engine fix or must fan out.

| file:line | reader pattern | tokens consumed | parser engine |
|---|---|---|---|
| apps/web/src/modules/catalog/components/viewer3d/lib/readMeshTokens.ts:12 | `getComputedStyle(document.documentElement).getPropertyValue(name).trim()` (generic reader fn) | `--color-viewer-mesh-paint`, `--color-viewer-mesh-edge`, `--color-viewer-grid`, `--color-viewer-measure` (consumed via callers on lines 18–21) | three.js (value is then wrapped in `new Color(...)` by callers, lines 18–21) |
| apps/web/src/modules/catalog/components/viewer3d/lib/readMeshTokens.ts:18 | `new Color(readVar("--color-viewer-mesh-paint", "hsl(220 9% 60%)"))` | `--color-viewer-mesh-paint` | three.js |
| apps/web/src/modules/catalog/components/viewer3d/lib/readMeshTokens.ts:19 | `new Color(readVar("--color-viewer-mesh-edge", "hsl(220 14% 28%)"))` | `--color-viewer-mesh-edge` | three.js |
| apps/web/src/modules/catalog/components/viewer3d/lib/readMeshTokens.ts:20 | `new Color(readVar("--color-viewer-grid", "hsl(220 14% 80%)"))` | `--color-viewer-grid` | three.js |
| apps/web/src/modules/catalog/components/viewer3d/lib/readMeshTokens.ts:21 | `new Color(readVar("--color-viewer-measure", "hsl(217 91% 60%)"))` | `--color-viewer-measure` | three.js |
| apps/web/src/modules/catalog/components/viewer3d/lib/palette.ts:16 | `new Color().setRGB(r, g, b, LinearSRGBColorSpace)` | none — values are derived programmatically from OKLCH math (see `oklchOf`/`oklchToLinearSrgb`), not from CSS tokens | three.js (but not a token reader — algorithmic) |
| apps/web/src/modules/catalog/components/viewer3d/Viewer3DCanvas.tsx:278 | `gl.setClearColor(new Color(0x000000), 0)` | none — hard-coded hex literal for transparent clear (alpha=0) | three.js (but not a token reader — fixed clear color) |

## Conclusions

**Totals by parser engine**
- `three.js`: 7 total `new Color(...)` sites
  - **Token-consuming readers: 4** (all in `readMeshTokens.ts`, lines 18–21, fed via the single `getComputedStyle`/`getPropertyValue` call on line 12)
  - **Non-token sites: 3** (`palette.ts:16` algorithmic, `Viewer3DCanvas.tsx:278` hard-coded transparent clear; `palette.ts:16` is included for completeness — it does not parse a token string)
- `browser`: 0 explicit `getPropertyValue('--color-…')` sites outside `readMeshTokens.ts`. All other token consumption happens via Tailwind utility classes resolved by the browser CSS engine at paint time; these are not "readers" in the audit sense.
- `other`: 0

**Decision K working-assumption check**
The brief assumed only `readMeshTokens.ts` and `palette.ts:10` are non-browser token readers. Adjusted reading:
- `readMeshTokens.ts` — **confirmed** as the single non-browser CSS-variable reader (line 12). All 4 viewer tokens flow through it.
- `palette.ts:10` — **not a token reader**. The brief reference was likely to `palette.ts:16` (`new Color().setRGB(...)`), but that call sources its RGB from the OKLCH algorithm (`oklchToLinearSrgb`), not from a CSS variable. Strictly speaking, `palette.ts` should be **dropped from the Decision K non-browser-reader list** — it never touches `getPropertyValue`. It remains a `new Color(...)` call site, which is relevant for the lint allow-list, but it is not a token consumer.

**Verdict: confirmed (with one clarification).** Non-browser token readers are limited to `readMeshTokens.ts:12,18-21`. No additional readers exist that would force Decision K to fan Story 5.5 across multiple parser engines.

**One additional `new Color(...)` site worth flagging for Decision K's lint allow-list:** `Viewer3DCanvas.tsx:278` (`new Color(0x000000)` for `setClearColor`). This is a fixed transparent clear, not a token consumer. The lint rule for Story 5.8 should allow `new Color(...)` invocations that take a numeric literal (`0x…` or RGB triple) and only flag string-argument forms that fail to come from a `readVar(...)`-style helper.

**No Decision K gating required.** Story 5.5 (token consumer audit) can proceed as a single-engine task scoped to `readMeshTokens.ts` plus the four `--color-viewer-*` tokens. Phase B granularity does not need to fan out.
