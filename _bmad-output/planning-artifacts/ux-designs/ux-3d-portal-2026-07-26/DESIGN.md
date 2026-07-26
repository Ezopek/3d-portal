---
name: 3d-portal — Catalog Discovery (Initiative 26)
description: Visual delta for the seven Initiative 26 catalog-discovery surfaces. Inherits the shipped shadcn/ui + Tailwind v4 token system in apps/web/src/styles/theme.css wholesale; introduces zero new --color-* tokens and specifies only role assignments, anatomy and sizing.
status: final
updated: 2026-07-26
colors:
  # INHERITED, NOT OVERRIDDEN. Values are quoted verbatim from
  # apps/web/src/styles/theme.css, which stays the single source of truth.
  # HSL (not hex) is the authoritative notation there; restating these in a
  # second notation would create a drift surface for zero benefit.
  # This pass introduces NO new token. Every entry below is listed only
  # because a component spec in this file references it.
  background: 'hsl(0 0% 100%)'
  background-dark: 'hsl(222 47% 7%)'
  foreground: 'hsl(222 47% 11%)'
  foreground-dark: 'hsl(210 40% 98%)'
  card: 'hsl(0 0% 100%)'
  card-dark: 'hsl(222 47% 11%)'
  card-foreground: 'hsl(222 47% 11%)'
  card-foreground-dark: 'hsl(210 40% 98%)'
  popover: 'hsl(0 0% 100%)'
  popover-dark: 'hsl(222 47% 11%)'
  popover-foreground: 'hsl(222 47% 11%)'
  popover-foreground-dark: 'hsl(210 40% 98%)'
  muted-foreground: 'hsl(216.923 20.635% 37.059%)'
  muted-foreground-dark: 'hsl(215 20% 65%)'
  primary: 'hsl(221 83% 53%)'
  primary-dark: 'hsl(217 91% 60%)'
  primary-foreground: 'hsl(0 0% 100%)'
  primary-foreground-dark: 'hsl(222 47% 11%)'
  accent: 'hsl(214.286 31.818% 91.373%)'
  accent-dark: 'hsl(216.667 30.508% 23.137%)'
  accent-foreground: 'hsl(222 47% 11%)'
  accent-foreground-dark: 'hsl(210 40% 98%)'
  border: 'hsl(214 32% 91%)'
  border-dark: 'hsl(217 33% 20%)'
  ring: 'hsl(221 83% 53%)'
  ring-dark: 'hsl(217 91% 60%)'
  warning: 'hsl(38 92% 50%)'
  warning-dark: 'hsl(38 92% 60%)'
  destructive: 'hsl(0 84% 60%)'
  destructive-dark: 'hsl(0 84% 70%)'
  # Theme-invariant by design (documented as such in theme.css) — the gallery
  # controls float over arbitrary photo content, so they do not flip.
  gallery-control: 'hsl(0 0% 0%)'
  gallery-control-foreground: 'hsl(0 0% 100%)'
typography:
  # Inherited from the shipped Tailwind/shadcn ramp (Inter, --font-sans).
  # No role is overridden by this pass; the two entries below exist only
  # because component specs reference them by name.
  rail-item:
    note: 'Inherited — Tailwind text-sm, default weight; font-medium when active.'
  rail-count:
    note: 'Inherited — Tailwind text-xs, tabular-nums, muted-foreground.'
rounded:
  # Inherited verbatim from theme.css @theme {}. No override.
  sm: 0.375rem
  md: 0.5rem
  lg: 0.75rem
  xl: 1rem
  full: 9999px
spacing:
  # Tailwind 4-based scale inherited as-is. Two named tokens are introduced
  # for this pass because they are load-bearing accessibility floors, not
  # aesthetic choices.
  target-min: 24px
  target-fullscreen-close: 44px
components:
  browse-rail-item:
    background: 'transparent'
    foreground: '{colors.muted-foreground}'
    radius: '{rounded.md}'
    minHeight: '36px'
  browse-rail-item-active:
    background: '{colors.primary} @ 10%'
    foreground: '{colors.foreground}'
    ring: '1px inset {colors.primary}'
    radius: '{rounded.md}'
  browse-rail-count:
    foreground: '{colors.muted-foreground}'
    background: 'none'
  browse-rail-item-empty:
    foreground: '{colors.muted-foreground} @ 60%'
  scope-chip:
    background: '{colors.primary} @ 10%'
    foreground: '{colors.foreground}'
    ring: '1px inset {colors.primary}'
    radius: '{rounded.md}'
    minHeight: '{spacing.target-min}'
  scope-chip-action:
    background: 'transparent'
    foreground: '{colors.foreground}'
    decoration: 'underline on hover/focus; primary separator remains the location cue'
    radius: '{rounded.sm}'
    minHeight: '{spacing.target-min}'
  suggestion-panel:
    background: '{colors.popover}'
    foreground: '{colors.popover-foreground}'
    border: '1px {colors.border}'
    radius: '{rounded.md}'
    elevation: 'shadow-lg'
  suggestion-row-query:
    background: 'transparent'
    foreground: '{colors.popover-foreground}'
    icon: 'lucide Search'
    minHeight: '36px'
  suggestion-row-tag:
    background: 'transparent'
    foreground: '{colors.popover-foreground}'
    icon: 'lucide Plus'
    minHeight: '36px'
  suggestion-tag-pill:
    background: '{colors.accent}'
    foreground: '{colors.accent-foreground}'
    radius: '{rounded.full}'
  suggestion-group-suffix:
    foreground: '{colors.muted-foreground}'
  suggestion-alias:
    foreground: '{colors.muted-foreground}'
  suggestion-overflow-note:
    foreground: '{colors.muted-foreground}'
    background: 'transparent'
  filters-trigger:
    background: 'transparent'
    foreground: '{colors.foreground}'
    border: '1px {colors.border}'
    radius: '{rounded.md}'
    minHeight: '{spacing.target-min}'
  filters-trigger-badge:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.full}'
  filters-surface:
    background: '{colors.card}'
    foreground: '{colors.card-foreground}'
    border: '1px {colors.border}'
  browse-sheet:
    background: '{colors.card}'
    foreground: '{colors.foreground}'
  model-detail-category-link:
    background: '{colors.primary} @ 10%'
    foreground: '{colors.foreground}'
    ring: '1px inset {colors.primary}'
    radius: '{rounded.md}'
  admin-category-row:
    background: '{colors.card}'
    border: '1px {colors.border}'
    radius: '{rounded.md}'
  admin-criterion-text:
    foreground: '{colors.muted-foreground}'
  admin-replace-set-editor:
    background: '{colors.card}'
    foreground: '{colors.card-foreground}'
    border: '1px {colors.border}'
    radius: '{rounded.lg}'
    elevation: 'shadow-lg'
  admin-replace-set-advisory:
    foreground: '{colors.foreground}'
    marker: '{colors.warning}'
    border: '1px {colors.border}'
    radius: '{rounded.md}'
  curation-warning-row:
    background: 'transparent'
    foreground: '{colors.foreground}'
    marker: '{colors.warning}'
    border: '1px {colors.border}'
    radius: '{rounded.md}'
  lightbox-toolbar:
    background: '{colors.gallery-control} @ 40%'
    foreground: '{colors.gallery-control-foreground}'
    radius: '{rounded.full}'
  lightbox-zoom-control:
    background: '{colors.gallery-control} @ 40%'
    foreground: '{colors.gallery-control-foreground}'
    radius: '{rounded.full}'
    size: '40px'
  lightbox-close:
    background: '{colors.gallery-control} @ 40%'
    foreground: '{colors.gallery-control-foreground}'
    radius: '{rounded.full}'
    size: '{spacing.target-fullscreen-close}'
---

# 3d-portal — Catalog Discovery Visual Spine

> Scope: the seven Initiative 26 surfaces named by `G26-UXGATE`. This file owns *how it looks*; `EXPERIENCE.md` owns *how it works* and references these tokens by name. Both spines win over any mockup, wireframe or import. Neither spine authorises implementation — see `EXPERIENCE.md` § Non-goals and § Story-entry gates.

## Brand & Style

3d-portal is a private, single-operator catalogue of 3D-printable models with a small member audience. Its established posture is *sober tool, not marketplace*: dense information, no marketing surface, no illustration, no celebratory motion. Initiative 26 does not change that posture — it adds a navigation layer that had been missing, and the visual discipline for the whole pass is **subtraction**.

The one aesthetic idea this pass introduces is a **place-vs-constraint contrast**, and it is carried entirely by tokens that already ship:

- **Where you are** — the browse category you are standing in — speaks in the *primary* vocabulary (`{colors.primary}` at 10% with a 1px inset primary ring). This is the same treatment the shipped `ModuleRail` already uses for the active module, so "which category am I in" reads as *location*, exactly like "which module am I in".
- **What you asked for** — the tags, statuses and sources you selected — speaks in the *accent* vocabulary (`{colors.accent}` / `{colors.accent-foreground}`). This is the same treatment the shipped `FilterRibbon` already uses for a selected-tag chip, so a tag suggestion looks like what it will become once selected.

That is the whole brand-layer delta. **This pass introduces no new `--color-*` token, no new font, no new radius and no new shadow.** Every colour it names is already declared in `apps/web/src/styles/theme.css` with a matching `.dark` value, which is what makes `NFR26-DARKMODE-1` (token-only, light + dark, zero colour literals) satisfiable by construction rather than by review.

## Colors

No token is added, removed or re-valued. What follows is the **role assignment** — which existing token means what on these surfaces, and what it must not be used for.

- **`{colors.primary}` at 10% + inset primary ring — "location".** Used on exactly three things: the active browse-rail row, the category scope chip above the results, and a category link on the model-detail surface. It answers *where am I / where does this take me*. **Never** used for a tag, a status, a source, or a sort. Solid `{colors.primary}` remains what it already is: the filled state of a primary button and the `Filters (n)` badge fill.
- **`{colors.accent}` / `{colors.accent-foreground}` — "constraint you chose".** Used on selected tag chips (shipped) and on the `+tag` pill inside the suggestion list. It answers *what did I narrow by*. **Never** used for a category, and never used to indicate hover on a row that also carries an accent chip — that collision is why the rail uses primary, not accent, for its active state.
- **`{colors.muted-foreground}` — "true but secondary".** Category counts, the tag-group suffix in a suggestion pill, the matched-alias hint, the suggestion overflow note, the inclusion criterion in the admin list, and every dimmed empty-category label. All of these are information the user reads *second*.
- **`{colors.warning}` — "advisory, never blocking".** The only colour permitted on the admin curation-QA surface. It marks a row that a human should look at. **Never** `{colors.destructive}` there: destructive means *this write failed / this will delete data*, and every curation finding is advisory by `FR26-ADMIN-2`.
- **`{colors.destructive}`** keeps its shipped meaning: failed writes, and the `409`-conflict delete path on the admin category surface.
- **`{colors.gallery-control}` / `-foreground` — theme-invariant, by design.** The lightbox chrome floats over arbitrary photography, so it does not flip with the theme; `theme.css` already documents this and this pass does not change it. Consequence for dark mode: the lightbox is the **only** surface in this pass whose chrome does not visibly differ between light and dark, and that is correct rather than an omission.

**Contrast targets for the load-bearing combinations.** These are the pairs a downstream story must actually verify, because they are the ones this pass creates or re-purposes:

| Combination | Target |
|---|---|
| Rail active row: `{colors.foreground}` on `{colors.primary}` @10% over `{colors.card}` | ≥ 4.5:1, light and dark |
| Rail count: `{colors.muted-foreground}` on `{colors.card}` | ≥ 4.5:1, light and dark |
| Scope chip label: `{colors.foreground}` on `{colors.primary}` @10% over `{colors.background}` | ≥ 4.5:1, light and dark |
| Scope chip action: `{colors.foreground}` on `{colors.primary}` @10% | ≥ 4.5:1; measured 15.576:1 light / 15.168:1 dark against the 2026-07-26 `theme.css` tokens |
| `+tag` pill: `{colors.accent-foreground}` on `{colors.accent}` | ≥ 4.5:1, light and dark |
| Suggestion group suffix / alias: `{colors.muted-foreground}` on `{colors.popover}` | ≥ 4.5:1, light and dark |
| Curation warning marker: `{colors.warning}` on `{colors.card}` | ≥ 3:1 (non-text indicator) |
| Focus ring: `{colors.ring}` against `{colors.card}` and `{colors.popover}` | ≥ 3:1 |
| Lightbox control glyph on `{colors.gallery-control}` @40% over a light photo | ≥ 3:1 (non-text) — the 40% scrim is the mechanism |

The dimmed empty-category label (`{colors.muted-foreground}` @ 60%) is deliberately **not** in that table: it is decorative de-emphasis on a row whose accessible name still carries the full label and count, so it is exempt from the text-contrast floor. That exemption is recorded here so a reviewer does not read it as a miss.

## Typography

Fully inherited — Inter via `--font-sans`, the Tailwind size ramp, no new role. Two conventions are worth stating because they are easy to get wrong:

- **Counts render in `tabular-nums`.** A rail of eight categories with proportional digits visibly jitters as counts change; the tabular variant costs nothing and keeps the right edge steady.
- **Category and tag labels are content, not chrome.** They come from `name_pl` / `name_en` on the entity and are selected by active locale with an `name_en` fallback — never from `i18next`. Only the surrounding UI chrome (the word "Filters", "Browse", "Search entire catalog") is an i18n key. This is the same split the shipped `FacetSidebar.labelOf` and `TagGroupsSection.labelOf` already implement, and the same guard applies: an **empty-string** `name_pl` is treated as absent and falls back to `name_en`.

## Layout & Spacing

Tailwind's 4-based scale, inherited. Two breakpoint regimes, both already real in the codebase:

| Regime | Trigger | Browse | Filters |
|---|---|---|---|
| Desktop | `lg` (1024px+) | Persistent left rail, `w-60`, `border-r`, matching the shipped `ModuleRail` and `FacetSidebar` width so the two columns align | Right-side panel/drawer |
| Compact | below `lg` | `Sheet` from the left, opened from a toolbar control | `Sheet` from the bottom |

The rail is `w-60 shrink-0 border-r border-border bg-card` — the exact geometry `FacetSidebar` occupies today, so the browse-IA cutover is a swap in one column rather than a reflow of the grid.

The result grid, its pagination and its empty states keep their shipped geometry unchanged. The scope chip inserts one full-width row between the toolbar and the grid; nothing else moves.

**Two named spacing tokens are load-bearing accessibility floors, not aesthetics.** `{spacing.target-min}` (24px) is the minimum hit area for every interactive control introduced by this pass (WCAG 2.2 SC 2.5.8). `{spacing.target-fullscreen-close}` (44px) is the fullscreen-viewer close control specifically, per the operator packet. They are tokens so a story cannot quietly ship a 20px chip action.

## Elevation & Depth

Inherited, and deliberately thin. The suggestion panel and the two sheets carry the shipped shadcn popover/sheet elevation; the rail, the scope chip and the promoted-filter row are **flat** — separated by `{colors.border}`, never by a shadow. Depth in this product means *this floats above and will go away*; a scope chip does not go away, so it must not float.

The lightbox is the one place where layering is structural rather than decorative: its toolbar sits **outside** the transformed image layer, so it never scales, translates or blurs with the image. That is a behavioural contract stated in `EXPERIENCE.md`; visually it means the toolbar keeps a constant size and a constant 40% scrim at every zoom level.

## Shapes

Inherited: `{rounded.sm}` for small inline actions, `{rounded.md}` for rows, chips, panels and the scope chip, `{rounded.full}` for the `+tag` pill, the `Filters (n)` badge and every circular lightbox control.

One deliberate shape distinction: **the scope chip is `{rounded.md}`, the tag pill is `{rounded.full}`.** Shape alone is not sufficient to distinguish them (see the three-channel rule in `EXPERIENCE.md` § Accessibility Floor), but it is a free reinforcement of the place-vs-constraint contrast, and it means a screenshot at any zoom still separates the two.

## Components

Visual specs. Behaviour, states and keyboard contracts live in `EXPERIENCE.md` § Component Patterns.

→ Rendered at 1:1 in [`mockups/key-desktop-browse.html`](mockups/key-desktop-browse.html) (rail, rail states, scope chip, Filters trigger — light **and** dark), [`mockups/key-suggestions-and-mobile.html`](mockups/key-suggestions-and-mobile.html) (suggestion panel anatomy, tag pill, group suffix, alias, overflow note, Browse sheet), [`mockups/key-viewer-chrome.html`](mockups/key-viewer-chrome.html) (toolbar, zoom controls, 44×44 close) and [`mockups/key-admin-curation.html`](mockups/key-admin-curation.html) (admin row, criterion text, curation warning row). **The spines win on conflict.**

| Component | Anatomy | Visual spec |
|---|---|---|
| **Browse rail** | `<nav>` column, `w-60`, `bg-card`, `border-r border-border`; first row is always "All catalog", then categories ordered by `(position, slug)` | Rows are `{components.browse-rail-item}`: `min-h-9`, `{rounded.md}`, label left, count right |
| **Rail row — active** | Same row, current scope | `{components.browse-rail-item-active}` — `bg-primary/10`, `ring-1 ring-inset ring-primary`, `font-medium`, `text-foreground`. Identical to the shipped `ModuleRail` active treatment |
| **Rail row — count** | Trailing number | `{components.browse-rail-count}` — `text-xs tabular-nums text-muted-foreground`, no badge, no pill, no background |
| **Rail row — empty category** | `model_count === 0` | `{components.browse-rail-item-empty}` — label at 60% muted; still focusable, still navigable, never hidden |
| **Browse sheet (compact)** | Left `Sheet`, `w-80 max-w-[85vw]` | `{components.browse-sheet}` — same row vocabulary as the rail, one column, no second nesting level |
| **Scope chip** | Icon + category label + separator + trailing action | `{components.scope-chip}` — `bg-primary/10`, `ring-1 ring-inset ring-primary`, `{rounded.md}`, `min-h-6`. Full-width row above the grid, not an inline pill in a chip row |
| **Scope chip action** | Text button inside the chip | `{components.scope-chip-action}` — `text-foreground`, underline on hover/focus, primary separator retained, `min-h-6 min-w-6`. **Text label, never a bare `×` glyph** |
| **Suggestion panel** | Popover anchored to the search input, width = input width | `{components.suggestion-panel}` — `bg-popover`, `border-border`, `{rounded.md}`, `shadow-lg`. **Height is content-driven; `overflow: visible`, no `max-h`, no internal scrollbar** |
| **Suggestion row — plain query** | Magnifier glyph + the typed text | `{components.suggestion-row-query}` — `min-h-9`, plain `text-popover-foreground`, no pill. Always the first row |
| **Suggestion row — `+tag`** | Plus glyph + pill + optional group suffix + optional alias | `{components.suggestion-row-tag}` + `{components.suggestion-tag-pill}` (`bg-accent`, `{rounded.full}`) + `{components.suggestion-group-suffix}` (` · Zastosowanie`, muted) + `{components.suggestion-alias}` (muted, smaller) |
| **Suggestion overflow note** | Trailing line when more tags matched than fit | `{components.suggestion-overflow-note}` — muted, **non-interactive**, no hover state, no focus stop. Points at Filters as the exhaustive surface |
| **Filters trigger** | Sliders glyph + "Filters" + count badge | `{components.filters-trigger}` + `{components.filters-trigger-badge}` (`bg-primary`, `{rounded.full}`). Badge is omitted entirely at `n === 0` — never rendered as `0` |
| **Filters surface** | Bottom `Sheet` (compact) / right panel (desktop) | `{components.filters-surface}` — `bg-card`, `border-border`. Contains the relocated facet-group list verbatim, then status / source / sort |
| **Promoted group control** | Group label + dropdown, horizontal row above the grid | Shipped `Select` trigger vocabulary, unchanged. Desktop only, at most two. **Off by default** — see `EXPERIENCE.md` § Non-goals |
| **Model-detail category link** | Category label, navigates to `/categories/{slug}` | `{components.model-detail-category-link}` — the location vocabulary again, so it is visibly *not* one of the accent tag chips sitting next to it |
| **Admin category row** | Slug · both labels · position · count · criterion · row menu | `{components.admin-category-row}` + `{components.admin-criterion-text}` (muted, single line, `truncate`). Criterion is visible **in the list**, not only in the edit dialog |
| **Curation warning row** | Warning marker + finding + affected entity + fix link | `{components.curation-warning-row}` — `{colors.warning}` marker only; body text stays `{colors.foreground}`. Never `{colors.destructive}` |
| **Lightbox toolbar** | Container for zoom controls + close | `{components.lightbox-toolbar}` — constant size at every zoom level, **outside** the transform layer |
| **Lightbox zoom control** | Zoom in / Zoom out / Reset, three separate buttons | `{components.lightbox-zoom-control}` — 40px circular, `{colors.gallery-control}` @40% scrim. Always mounted; never part of the tap-to-hide chrome layer |
| **Lightbox close** | `×` glyph | `{components.lightbox-close}` — **44×44 minimum**, `{spacing.target-fullscreen-close}`. Larger than every other control on the surface, deliberately |

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use `{colors.primary}` @10% + inset ring for *location* (rail active, scope chip, model-detail category link) | Use it for a tag, a status, a source or a sort |
| Use `{colors.accent}` for *a constraint the user chose* (selected tag chip, `+tag` pill) | Use it for a category anywhere |
| Render category counts as muted `tabular-nums` text | Render them as a badge — a badge reads as a notification |
| Give the scope-chip escape a visible text label | Ship a bare `×`, which reads as "remove" and hides that the query survives |
| Let the suggestion panel size to its content, capped at 8 rows | Add `max-h` + `overflow-y-auto` — an internal scrollbar is explicitly banned |
| Distinguish the query row from a `+tag` row by glyph **and** shape **and** accessible name | Rely on colour or position alone |
| Keep the lightbox zoom controls mounted at every chrome state | Fold them into the tap-to-hide chrome layer |
| Take every colour from a `--color-*` token | Write a hex literal, an `rgba()`, or a Tailwind palette colour (`bg-blue-500`) |
| Mark curation findings with `{colors.warning}` | Mark them with `{colors.destructive}` — nothing there is destructive |
| Keep the rail at `w-60` so it aligns with the shipped `ModuleRail` | Introduce a third column width in the same viewport |
