---
artifact: ux-recommendation
topic: stl-slicer-estimate-display-catalog-filestab
designer: Sally
date: 2026-06-02
bmad_route: bmad-ux (Create UX, menu-code CU, phase 2-planning) — confirmed via session-start bmad-help; brownfield discovery-only carve-out, output under _bmad-output/ux/ per AGENTS.md tracked surface
scope: UIX/product discovery ONLY — no frontend/backend/infra/test/config code
predecessors:
  - Story 32.6 (shipped) — estimates module: EstimateDisplay, PrintIntentPresetSelector, useEstimate, GET /api/estimates read seam
  - deferred-work.md — EST-INGEST-1 (part→stl_hash linkage), EST-RECOMPUTE-1 (enqueue), SW-DEPLOY-1
downstream: bmad-correct-course (epic/story split) → bmad-create-story for the read/display story
status: ready-for-operator-review
live_example: https://3d.ezop.ddns.net/catalog/4f3aa7f1-a72f-4925-832d-defd9dbefc96
mockups:
  - mockups/stl-estimate-desktop.html
  - mockups/stl-estimate-mobile.html
---

# STL Slicer-Estimate Display — Catalog → FilesTab → STL List (UX Discovery)

**Author:** Sally (UX Designer) — 2026-06-02
**Surface:** `CatalogDetail` → `FilesTab` (`active === "stl"`) → the STL `<ul>` row list.
**Goal:** Make the estimated **filament gramature** the first user-visible slicer-estimate datum in the catalog, inline and scan-worthy, without promising a quote or implying live auto-update.

> **Routing note (mandatory protocol):** `bmad-help` was invoked at session start. The catalog's closest canonical UIX route is **`[CU] Create UX` (`bmad-ux`, phase 2-planning, preceded-by `bmad-prd`)**. This is brownfield (PRD/architecture/epics exist) and the operator scoped the task as *discovery-only* with an explicit deliverable shape, so this is authored as a focused UX recommendation under the `bmad-ux` output surface (`_bmad-output/ux/**/*.md`, a git-tracked path per AGENTS.md). No PRD/architecture/code touched. Next ceremony for turning this into work is `bmad-correct-course` (epic/story split) → `bmad-create-story`.

---

## TL;DR — recommendation

1. **One global preset bar above the STL list** (member-visible), a compact horizontal form of the shipped `PrintIntentPresetSelector` (Material · Quality · optional Pinned filament). One selection re-keys every row's estimate + the expanded panel. **Not** per-row.
2. **Collapsed STL row carries an inline estimate chip** — a tasteful filament-spool icon + **grams only** (`🧵 42 g`), right-aligned into a consistent column so grams scan vertically down the list. Filename truncates first; the chip never truncates.
3. **The chip shows grams only.** Time/length/volume/**cost** live exclusively in the expanded panel. Cost never appears at-a-glance (avoids reading as a quote).
4. **Expanded 3D preview embeds the full shipped `EstimateDisplay`** as a secondary detail beside/below the viewer — grams appear in *both* (chip = scan, panel = breakdown), reusing the 32.6 component 1:1.
5. **Estimate chip is read-only and member-visible.** It is visually and semantically separated from the admin-only `selected_for_render` checkbox and the admin **Re-render preview** button — those drive the *snapshot preview render*, a different pipeline. No enqueue/recompute affordance in this story.
6. **Every state renders honestly and mutually-exclusively** in the chip: `absent / loading / fresh / stale / queued / failed / network-error`. Copy reuses shipped `modules.estimates.*` keys for the panel and adds short `modules.estimates.chip.*` tooltip/aria keys for the chip.

---

## Constraints in force (from operator brief + code reality)

- **Grams MUST be inline in the *collapsed* row**, not only behind the expanded preview — only one row can be expanded at a time, and grams are the scan target.
- **Prefer a tasteful filament icon** next to grams.
- **Profile selector is global** for the STL list/model, not per-row (operator decision; confirm scope in Open Questions Q1/Q7).
- **No quote, no auto-update promise.** Cost, if shown at all, is informational only (`modules.estimates.cost_informational` — "Informational only — not a quote.").
- **Admin profile/settings management (filament/profile add/remove/import/defaults/mapping) is explicitly OUT** of the first frontend story — a later separate Admin Panel story.
- **No EST-INGEST-1 / EST-RECOMPUTE-1 / enqueue / recompute / admin profile work** is designed here beyond noting the dependency and the story split.
- Frontend rule: **zero inline hex** in components — theme tokens only (`--color-warning hsl(38 92% 50%)`, `bg-card`, `border-border`, `text-muted-foreground`, etc.). The static HTML mockups approximate the tokens for illustration; production uses Tailwind/theme classes.

---

## Current state (read from code, 2026-06-02)

`apps/web/src/modules/catalog/components/tabs/FilesTab.tsx` collapsed STL row, left→right:

```
[admin ☐]  [#idx]  stl  filename……………………(flex-1 truncate)  12.4 MB  [▸ ⬚ preview]  [⬇]
```

- `selected_for_render` checkbox: `isAdmin && isStl`, far left.
- `#idx`: STL position (`stlIndex.positionOf`), mono.
- `stl` literal kind label, mono — **redundant** inside the STL-filtered tab.
- filename: `flex-1 truncate`.
- size: `fmtSize()`, `text-muted-foreground`.
- preview toggle: chevron + `Box`; only one row expands (`expandedFileId` is a single id).
- download anchor.
- Admin-only above the list: **Upload**, `checkedHelp` text + **Re-render preview** (`triggerRender`, snapshot/trimesh — *not* slicer).

Estimates module already shipped (Story 32.6) but **not wired into catalog** (EST-INGEST-1 deferred — no part→`stl_hash` linkage yet):

- `EstimateDisplay` — full panel; renders `loading / error / absent / failed / fresh / stale / queued` honestly; mass via `formatMass` → `"42 g"` / `"1.20 kg"`, em-dash on null/non-finite; never silent-zero.
- `PrintIntentPresetSelector` — Material ∈ {PLA,PETG,PCTG,TPU} (untranslated), Quality ∈ {aesthetic,standard,strong}, optional pinned Spoolman filament by churn-stable `filamentRef`.
- `useEstimate` hook over `GET /api/estimates`; `EstimateView` DTO carries `status, time_seconds, filament_g, filament_mm, filament_cm3, filament_cost, currency, computed_at, warnings, failure_reason, override_context`.

**This surface is the first place a member sees a slicer estimate in the catalog.** It is a wiring + presentation story over already-shipped primitives — *not* new estimate logic.

---

## Recommendation detail

### A. Global preset bar (member-visible)

Mounts inside the STL tab, **above** the `<ul>`, only when `active === "stl"` and `stlFiles.length > 0`. It is the compact, horizontal projection of `PrintIntentPresetSelector`:

```
┌─ Estimate profile ─────────────────────────────────────────────────────┐
│  Material [PLA ▾]   Quality [Standard ▾]   Filament [No pin ▾]          │
│  Estimates below use this profile · informational, not a quote          │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Member-visible**, not gated on `isAdmin`. Any logged-in viewer can re-key the estimates they see.
- A single source of truth (one preset object) feeds every row chip *and* the expanded panel. Changing it re-queries all visible rows (one estimate read per STL, keyed by that part's `stl_hash` + the resolved preset bundle).
- **Desktop:** three native `<select>`s in a row, small muted labels above each (matches the shipped selector's native-label-for-a11y pattern). Helper line beneath in `text-muted-foreground`.
- **Mobile:** collapses to a single tappable summary chip `PLA · Standard · No pin` that opens a disclosure/sheet containing the three selects stacked full-width. Saves vertical space above a potentially long list.
- **Dark/light:** `bg-card` / `border-border` / `text-foreground` + `text-muted-foreground`; no hex.
- **Long filenames:** the preset bar is full-width and independent of row width, so it is unaffected. (Row truncation handled in §B.)
- **Spoolman empty/unavailable:** the pinned-filament select shows only "No pin (material default)" — acceptable, the material default path is always valid (confirm Q8).

### B. Collapsed row content hierarchy

Proposed row, left→right (changes vs current in **bold**):

```
[admin ☐]  [#idx]  filename……………(flex-1 truncate)  [🧵 42 g]  12.4 MB  [▸ ⬚]  [⬇]
                                                       ▲ estimate chip (NEW)
```

Hierarchy / scan rationale:

1. **admin checkbox** — far left, admin-only, unchanged (render-selection; not an estimate control).
2. **#idx** — keep (cross-references the 3D viewer file index).
3. ~~`stl` kind label~~ — **drop inside the STL tab** (redundant; frees horizontal room for the chip on narrow widths). Minor, non-load-bearing.
4. **filename** — `flex-1 truncate`; **truncates first** under pressure.
5. **estimate chip** — fixed-ish slot, **right-aligned into a consistent column** so grams form a clean vertical scan line down the list. Filament-spool icon + mass. **Never truncates.**
6. **size** — unchanged, muted.
7. **preview toggle**, **download** — unchanged.

The chip is the most scan-worthy datum, so it gets a stable column position and a distinct (but quiet) visual weight — icon + tabular-nums grams. It does **not** out-shout the filename; it reads as metadata, not a CTA.

**Filament icon.** Lucide has no canonical spool glyph, so recommend a small **custom inline SVG spool** (24×24, `stroke="currentColor"`, inherits chip color → free dark/light + state tinting). Fallback if avoiding a custom asset: lucide `Disc3` or `Circle`. The icon is decorative (`aria-hidden`); grams carry the meaning.

**Chip content is grams-only.** No time/length/volume/cost in the collapsed row. This keeps the scan column clean and structurally prevents a cost number from reading as an at-a-glance quote. (Time-as-secondary is an explicit Open Question, Q3 — default: grams-only.)

### C. Expanded 3D preview — grams as secondary detail? **Yes.**

When a row expands (`isExpanded`), render the shipped **`EstimateDisplay`** panel as a secondary block beside/below `Viewer3DInline`, bound to the same global preset:

- It shows the full breakdown: Print time, Filament (mass), Length, Volume, Material cost (+ "Informational only — not a quote."), staleness/queued banners, "Last estimated HH:MM", slice warnings, and the `OverrideContextPanel` (material/quality/pinned/purchase link).
- Grams therefore appear in **both** places: the collapsed chip (primary scan) and the expanded panel (full detail). That is intentional, not duplication noise — different jobs (scan vs. inspect).
- Reuses the 32.6 component verbatim; the only new code is the chip + the preset bar + the wiring.

### D. Relation to admin `selected_for_render` + Re-render preview

Keep these **clearly separated** so the estimate never reads as triggering anything:

| Control | Audience | Pipeline | Relation to estimate |
|---|---|---|---|
| `selected_for_render` checkbox | admin only | snapshot/trimesh **preview** render | none — different render path |
| **Re-render preview** button | admin only | snapshot preview enqueue | none — does not slice/estimate |
| **Estimate chip** (new) | **member-visible** | slicer estimate **read** (`GET /api/estimates`) | read-only display |

- Chip lives in the member content zone (between filename and size); admin controls bookend the row (checkbox far-left, preview/download right). No shared affordance, no implied causality.
- The chip must not look clickable-to-recompute. Recompute is a *future* story (EST-RECOMPUTE-1), not this one.

---

## State / copy table

Each estimate state is rendered **mutually-exclusively** in two registers: the **collapsed chip** (terse, icon + value + tooltip/aria) and the **expanded panel** (shipped `EstimateDisplay`, full sentences).

| State | Chip (collapsed) | Chip styling | Chip tooltip / aria (new `modules.estimates.chip.*`) | Expanded panel (shipped keys) |
|---|---|---|---|---|
| **loading** (transport) | skeleton shimmer in chip slot | `aria-busy`, muted | aria: "Loading estimate…" (`states.loading`) | spinner + `states.loading` |
| **absent** (200 store miss) | `🧵 —` muted (icon de-emphasized) | `text-muted-foreground` | "No estimate yet" (`chip.absent` ≈ `states.absent.body`) | `EmptyState` `states.absent.body` + override context |
| **fresh** | `🧵 42 g` | normal `text-foreground`, `tabular-nums` | "Estimated {time}" (`chip.fresh`) | full `<dl>`, **no** banner |
| **stale** | `🧵 42 g` + amber dot | `text-warning` accent (`--color-warning`) | "May be out of date" (`states.stale_banner`) | amber `states.stale_banner` + "Last estimated…" |
| **queued** | `🧵 42 g` + tiny spinner (last-known g) / `🧵 …` if none | muted + spin | "Recomputing…" (`states.queued_banner`) | `states.queued_banner` + last-known numbers |
| **failed** | `🧵 —` + small alert | `text-destructive` accent | "Couldn't estimate" (`chip.failed` ≈ `states.failed.title`) | `states.failed.title` + `failure.{reason}` |
| **network error** (per-row read failed) | `—` + small alert (non-blocking) | `text-destructive`, quiet | "Couldn't load estimate" (`states.error`) | retryable `EmptyState` `states.error` + Retry |

**Copy rules enforced:**

- **No quote language.** Mass/time/length/volume are physical facts; cost carries `cost_informational` ("Informational only — not a quote.") **only in the panel**, never in the chip.
- **No auto-update promise.** `stale`/`queued` say "may be out of date" / "Recomputing…" — they never claim the number will refresh itself live (honors the SPOOL-EVT-1 honesty constraint baked into 32.6).
- **Never silent-zero.** Missing/non-finite → em-dash (`formatMass` already guarantees this); the chip shows `—`, never `0 g`.
- **Cost is opt-in detail, never scan-level.** It stays behind the expand.
- New chip keys are short tooltip/aria strings; they must ship in **both** `en.json` and `pl.json` (i18n parity) when the story is built.

---

## Wireframes (ASCII)

### Desktop — STL tab, list with chips + one row expanded

```
 STL · 3   Source · 1   3MF · 1                         [⬚ Download all (5)]

 ┌─ Estimate profile ───────────────────────────────────────────────────┐
 │ Material [PLA ▾]   Quality [Standard ▾]   Filament [No pin ▾]         │
 │ Estimates below use this profile · informational, not a quote         │
 └───────────────────────────────────────────────────────────────────────┘
 (admin)  Check files to include in preview renders   [⟳ Re-render preview]
 ┌───────────────────────────────────────────────────────────────────────┐
 │ ☐  1  bracket_left_v3.stl ……………………………   🧵 42 g    12.4 MB   ▸⬚  ⬇ │
 │ ☐  2  bracket_right_v3.stl …………………………   🧵 44 g    12.6 MB   ▾⬚  ⬇ │
 │ ┌───────────────────────────────────────────────────────────────────┐ │
 │ │  [ inline 3D viewer ]        │  Print time  3h 12m                 │ │
 │ │                              │  Filament    44 g                   │ │
 │ │                              │  Length      14.7 m                 │ │
 │ │                              │  Volume      36.20 cm³              │ │
 │ │                              │  Material cost  5.20 PLN            │ │
 │ │                              │  Informational only — not a quote.  │ │
 │ │                              │  Material & overrides: PLA · Std    │ │
 │ └───────────────────────────────────────────────────────────────────┘ │
 │ ☐  3  base_plate.stl ……………………………………   🧵 —  ⚠   48.1 MB   ▸⬚  ⬇ │  ← failed
 └───────────────────────────────────────────────────────────────────────┘
```

### Mobile — collapsed preset, grams scan column preserved

```
 STL · 3   Source · 1   3MF · 1

 [ PLA · Standard · No pin ▾ ]          ← tap → sheet with 3 stacked selects

 ┌─────────────────────────────────────┐
 │ bracket_left_v3.stl                  │
 │ 🧵 42 g        12.4 MB     ▸⬚   ⬇   │
 ├─────────────────────────────────────┤
 │ bracket_right_v3.stl                 │
 │ 🧵 44 g        12.6 MB     ▸⬚   ⬇   │
 ├─────────────────────────────────────┤
 │ base_plate.stl                       │
 │ 🧵 —  ⚠        48.1 MB     ▸⬚   ⬇   │
 └─────────────────────────────────────┘
```

On mobile the filename takes its own line and `🧵 grams` leads the metadata line, so the grams scan column survives the narrow width (chip never wraps under the size).

See the rendered static mockups:
- Desktop: [`mockups/stl-estimate-desktop.html`](mockups/stl-estimate-desktop.html)
- Mobile: [`mockups/stl-estimate-mobile.html`](mockups/stl-estimate-mobile.html)

---

## Mobile notes

- **Preset bar collapses** to a one-line summary chip → opens a sheet/disclosure (reuses the app's sheet pattern). Avoids three full-width selects permanently eating the top of a long list.
- **Row reflow:** filename on its own line, metadata line `🧵 g · size · preview · download`. Grams lead the metadata line so the scan column is preserved.
- **Tap targets:** preview toggle and download stay ≥ 40px; the chip is non-interactive (no tap target needed) — tooltip content is surfaced via the expanded panel on touch (no hover).
- **Expanded panel** stacks **below** the viewer on mobile (the desktop side-by-side becomes vertical); `EstimateDisplay`'s `grid-cols-2` already reflows acceptably.

## Accessibility notes

- **Chip is not a control** — render as a `<span>` with the spool SVG `aria-hidden` and an accessible text/`title` conveying state, e.g. `aria-label="Estimated filament 42 g, may be out of date"`. Don't make a non-actionable chip focusable.
- **State by more than color:** stale/failed pair the color accent with a glyph (amber dot / `AlertTriangle`) and text, so color-blind users aren't reliant on hue. Em-dash + alert icon ≠ a faint gray number.
- **Loading uses `aria-busy`/`role="status"`** (mirrors shipped `EstimateDisplay`), never an empty silent gap that reads as "no estimate".
- **Preset selects** keep the shipped native-`<select>` + `<label htmlFor>` pattern — keyboard-navigable by construction.
- **Live region discipline:** the per-row chip should not spam screen readers when a global preset change re-keys 20 rows. Recommend the *list* announces "Estimates updated for {n} files" once (a single polite live region on the list), and individual chips update silently. (Confirm interaction model in Q3/Q6.)
- **`tabular-nums`** on grams so the scan column stays digit-aligned.
- Color contrast: `--color-warning` and `text-destructive` accents must meet AA against `bg-card` in both themes — verify at build (visual regression covers the snapshot, but contrast is a manual check).

---

## Open questions for Ezop (only those that change the next story)

1. **Preset persistence/scope.** Global to the STL list is decided — but persisted *where*? Ephemeral (component state, resets on navigate) / per-session (`sessionStorage`) / per-user (server) / per-model? This decides where state lives and whether the read story needs any persistence at all. *(Recommend: ephemeral or `sessionStorage` for v1; no server state.)*
2. **Data availability gate (load-bearing).** EST-INGEST-1 (part→`stl_hash`) is deferred, so today there is **no** real catalog hash to read estimates by. Does the first FE story (a) **depend on EST-INGEST-1 landing first** (real numbers), or (b) ship the surface against a known/stub hash behind a flag (visible scaffolding, no real data)? This gates the whole sequencing. *(Recommend: sequence EST-INGEST-1 before/with the display story; otherwise the chip is permanently `absent`.)*
3. **Time in the collapsed chip?** Grams-only (recommended, cleanest scan) vs. `42 g · 3h 12m` secondary. Affects chip width and mobile reflow.
4. **Stale/queued numbers in the chip:** show last-known grams with an accent, or collapse to `—` + status glyph? *(Recommend: show last-known + accent — more useful, still honest.)*
5. **Does the chip ever appear for non-STL kinds (Source/3MF)?** *(Recommend: STL only — estimates are per-sliced-STL.)*
6. **Re-key UX when preset changes:** do all visible chips flip to skeleton simultaneously, or keep last value dimmed until the new read resolves? Affects perceived jank on a long list. *(Recommend: keep last value dimmed → swap, no full-list skeleton flash.)*
7. **Truly one global preset for the whole list?** Multi-part models could want different material per part. Confirm global-only for v1 (per-part is a bigger story).
8. **Spoolman unavailable/empty:** pinned-filament select shows only "No pin". Acceptable for v1, or surface a hint? *(Recommend: acceptable; material-default path is always valid.)*
9. **Cost visibility ceiling:** confirm cost stays *panel-only* and never enters the collapsed chip (recommended, to avoid at-a-glance quote reading).

---

## Proposed story split

Pure read/display is deliberately separated from enqueue/recompute and from admin profile management.

| Story | Title | Scope | Touches | Depends on |
|---|---|---|---|---|
| **EST-INGEST-1** (backend, prereq) | Catalog part → `stl_hash` ingestion | Hash catalog STLs, persist part→`stl_hash` map, trigger first resolve/slice. Feeds real hashes to the read seam. | `apps/api/.../catalog`, `EstimateStore`, slicer-worker overlay (**SW-DEPLOY-1** applies) | — |
| **Story A — THIS surface (read/display)** | STL list estimate display | Global preset bar + collapsed-row grams chip + expanded-panel `EstimateDisplay` wiring. **Read-only** via `GET /api/estimates`. Renders all states honestly. **No** enqueue, **no** admin profile mgmt. | `apps/web/.../catalog/FilesTab` + reuse `apps/web/.../estimates/*`; new `chip` i18n keys (en+pl) | EST-INGEST-1 (for real data) — or ship behind known-hash/flag per Q2 |
| **EST-RECOMPUTE-1** (follow-up) | User-driven "recompute now" | Guarded `POST /api/estimates/recompute` + a recompute affordance on `absent`/`stale`. | new estimates router (reuses 32.4 enqueue), slicer-worker overlay (**SW-DEPLOY-1** applies) | Story A, EST-INGEST-1 |
| **Admin profile mgmt** (separate Admin Panel initiative) | Filament/profile add·remove·import·defaults·mapping | Admin-only CRUD + defaults + Spoolman mapping management. **Explicitly out** of Story A. | Admin Panel module | own initiative |

**Sequencing recommendation:** EST-INGEST-1 → Story A (read/display) → EST-RECOMPUTE-1; Admin profile management is an independent later initiative. Story A is the smallest honest unit that satisfies the operator goal *"estimated gramature visible inline in the collapsed STL row"* — but it only shows **real** numbers once EST-INGEST-1 supplies per-part hashes (Q2). If the operator wants the surface visible sooner, Story A can ship against a known/stub hash behind a flag and light up when EST-INGEST-1 lands.

---

## Handoff

- **Next BMAD step:** `bmad-correct-course` to fold this into the epic/story structure (it owns post-ship scope changes), then `bmad-create-story` for Story A once Q1/Q2/Q3 are answered.
- **Reuse, don't re-author:** `EstimateDisplay`, `PrintIntentPresetSelector`, `OverrideContextPanel`, `useEstimate`, `format.ts`, and all shipped `modules.estimates.*` copy. New surface = preset bar (compact projection) + grams chip + wiring + short `chip.*` i18n keys.
- **Visual regression:** any implementing story must run `npm run test:visual` (AGENTS.md UI-change gate) and add baselines for the chip states + collapsed/expanded row.
