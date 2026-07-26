---
name: 3d-portal — Catalog Discovery (Initiative 26)
status: final
updated: 2026-07-26
scope: 'Targeted G26-UXGATE pass — seven no-SoT surfaces only. Not a whole-product UX pass.'
sources:
  - _bmad-output/planning-artifacts/prd.md § Initiative 26 (FR26-CAT/SEARCH/BROWSE/ADMIN/GOV/VIEW, NFR26-*)
  - _bmad-output/planning-artifacts/architecture.md § Initiative 26 (Decisions AX, AY, AZ, BA)
  - _bmad-output/planning-artifacts/epics.md § Initiative 26 (E48 shipped, E49–E54)
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-26-init26-catalog-discovery.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-07-26.md
  - /tmp/3d-portal-init26-correct-course-input.md (operator packet + 18-source research registry)
  - docs/design/HANDOFF-tagi-fasetowe.md (Initiative 25 facet-tag handoff — context, superseded for navigation only)
  - apps/api/app/core/db/seed.py § STARTER_TAXONOMY (shipped facet vocabulary — 8 groups / 36 tags)
gates_closed_by_this_pass:
  - G26-UXGATE
  - G26-CAT-SET
---

# 3d-portal — Catalog Discovery Experience Spine

> This file owns *how it works*. `DESIGN.md` owns *how it looks* and is referenced here by `{token}` name. Both spines win over any mockup, wireframe or import.
>
> **This spine is a design contract, not an implementation authorisation.** No code is written from it until each consuming story passes `bmad-create-story` + `bmad-create-story:validate` and the controller confirms that specific story under the standing initiative authorisation (`G26-DEVGO`). See § Story-entry gates.

## Foundation

Single responsive web surface. React 19 + TanStack Router/Query, shadcn/ui on Tailwind v4, tokens in `apps/web/src/styles/theme.css`. `DESIGN.md` is the visual identity reference and names the delta; this spine specifies only the behavioural delta on top of the shipped app.

Audience is small and known: one operator/admin (**Michał**) plus authenticated members. Every surface in this pass is behind `current_user` — none of it is anonymous, and none of it touches the anonymous `/share/$token` projection.

The product carries **two independent classification vocabularies**, and keeping them independent is the whole point of this pass:

| | **Category** | **Tag** |
|---|---|---|
| Answers | *What kind of thing do I want to browse?* | *What exact properties should it have?* |
| Cardinality | Many per model; **one** active scope at a time in the public UI | Many per model; many selected at once |
| Lives in | the **path** — `/categories/{slug}` | **query params** — `tag_ids`, `tag_match`, `untagged` |
| Surface | navigation (rail, Browse sheet, scope chip) | refinement (`Filters (n)`, `+tag` suggestions) |
| Counts toward `Filters (n)` | **No, never** | Yes |
| Governance | admin category surface | admin tag-group surface (shipped) |
| Generated from the other? | **Never**, in either direction | **Never** |

Facet semantics are untouched: **OR within one `TagGroup`, AND between `TagGroup`s**, with `tag_match` as the user override. **Category scope is never folded into `tag_match`.**

## Information Architecture

| Surface | Reached from | Purpose | Owning story |
|---|---|---|---|
| Catalog (unscoped) | `/catalog`, rail "All catalog", ModuleRail | Whole catalogue, no browse scope | shipped |
| Category browse | `/categories/{slug}` — rail row, Browse sheet row, model-detail category link, suggestion? no | One browse scope + the full refinement surface | 51.2 |
| Desktop browse rail | Persistent, `lg`+ | Broad categories + counts + "All catalog" | 51.1 |
| Browse sheet | Toolbar control, below `lg` | Same rows, one-column sheet | 51.3 |
| Scope chip | Rendered above the grid whenever a scope is active | Shows *where you are* + the one-click escape | 51.2 |
| Suggestion panel | Typing in the catalog search input | Plain query vs canonical `+tag`, ≤ 8 rows | 50.3 |
| `Filters (n)` | Toolbar control, both regimes | Tag groups, `Bez tagów`, status, source, sort | 52.1 |
| Model detail — categories | `/catalog/$modelId` | This model's categories, visually distinct from its tags | 51.4 |
| Admin — categories | `/admin/categories` tab | CRUD, reorder, criterion, replace-set assignment | 52.2 |
| Admin — curation QA | `/admin/categories` queue view | Six advisory hygiene checks | 52.3 |
| Fullscreen image viewer | Model gallery / share carousel | Mature zoom + pan + single-pointer alternatives | 53.2 |

**Nesting rule.** Modal depth stays at one level: a `Sheet` never opens another `Sheet`, and the lightbox never opens over an open sheet. The Browse sheet and the Filters sheet are siblings — opening one closes the other.

**Surface closure.** Every stated need in the packet lands on exactly one surface above, and every surface above is reached by at least one flow in § Key Flows. Nothing in this pass is reachable only by typing a URL.

→ Composition reference: [`mockups/key-desktop-browse.html`](mockups/key-desktop-browse.html) (desktop rail + scope chip, light and dark, plus the rail cold-load and rail-error states) · [`mockups/key-suggestions-and-mobile.html`](mockups/key-suggestions-and-mobile.html) (suggestion panel with accessible names shown, its two degraded states, the compact Browse sheet and the two toolbar triggers) · [`mockups/key-viewer-chrome.html`](mockups/key-viewer-chrome.html) (viewer chrome at rest / zoomed / chrome-hidden-while-zoomed / slow-load / image-error — **library-agnostic**) · [`mockups/key-admin-curation.html`](mockups/key-admin-curation.html) (admin category list with inline criteria, the six-check curation queue, the replace-set editor and the `409` delete path). **The spines win on conflict** — the mocks illustrate composition, they do not decide it.

## Browse Taxonomy — the starter category set (closes G26-CAT-SET)

Eight broad categories, inside the approved 6–10 band. **Every one cuts across at least two shipped tag groups** — that is the operational meaning of "a useful entry point for multiple models", and it is what stops a category from being a tag with a bigger font.

**The admission test** (`FR26-GOV-1`, made testable rather than rhetorical). A candidate is a **Category** only if all three hold:

1. it answers *what kind of thing am I looking for*, not *what property should it have*;
2. it is a plausible standalone landing page — someone would happily browse it with **zero** filters applied;
3. it survives the "still makes sense alone" check: if the candidate only makes sense as a narrowing of another set, it is a **Tag**.

Everything else is a Tag. A model may sit in several categories; the advisory norm is **1–3** (warning only, never a write block).

### The eight categories

| # | `position` | Slug | PL label | EN label |
|---|---|---|---|---|
| 1 | 0 | `storage-organization` | Przechowywanie i organizacja | Storage & Organization |
| 2 | 1 | `home-decor` | Dekoracje i wystrój | Home Decor |
| 3 | 2 | `holders-mounts` | Uchwyty i mocowania | Holders & Mounts |
| 4 | 3 | `electronics-cables` | Elektronika i kable | Electronics & Cables |
| 5 | 4 | `tools-workshop` | Narzędzia i warsztat | Tools & Workshop |
| 6 | 5 | `printer-3d` | Drukarka 3D i akcesoria | 3D Printer & Accessories |
| 7 | 6 | `toys-games` | Zabawki, gry i figurki | Toys, Games & Figures |
| 8 | 7 | `replacement-parts` | Części zamienne | Replacement Parts |

**Ordering rationale.** `position` runs broad-and-frequent first for this operator's catalogue (functional household printing), so the rail's top half carries the highest-traffic entry points and the count column does not need to be read to find them. Ordering is **content, not schema** — Story 49.2 may reorder on real distribution without touching any of this spine's other decisions.

### Per-category governance record

Each entry carries the `FR26-GOV-1` payload: one-sentence inclusion criterion, positive examples, boundary/non-examples with the tie-break, and the tag groups it crosses.

---

**1 · `storage-organization` — Przechowywanie i organizacja / Storage & Organization**

- **Inclusion criterion:** the model's primary purpose is to hold, sort or tidy *other* objects.
- **Positive examples:** Gridfinity bins and baseplates, drawer inserts, desk and drawer organizers, stackable boxes, wall-mounted racks, tool caddies, screw-sorting trays.
- **Boundary / non-examples:** a decorative bowl that happens to collect keys → **Dekoracje i wystrój** (the reason it is chosen is how it looks); a phone stand → **Uchwyty i mocowania** (it positions *one* object, it does not tidy several); a plant pot → **Dekoracje i wystrój** (holds soil, but the browse intent is decor).
- **Crosses tag groups:** Typ (Pojemniki, Organizery), System (Gridfinity, Multiboard, Bin Shells), Zastosowanie (Przechowywanie, Wkładki), Pomieszczenie (Kuchnia, Biurko).

**2 · `home-decor` — Dekoracje i wystrój / Home Decor**

- **Inclusion criterion:** the model is chosen mainly for how it looks in a living space, not for a job it performs.
- **Positive examples:** vases, decorative lamps and lampshades, wall art and reliefs, plant pots and planters, seasonal ornaments, display pieces.
- **Boundary / non-examples:** an articulated dragon → **Zabawki, gry i figurki** (play/collectible intent dominates); a lamp mounting bracket → **Uchwyty i mocowania**; a kitchen container in a pleasant colour → **Przechowywanie i organizacja** (function dominates; colour is not an intent).
- **Crosses tag groups:** Typ (Dekoracje, Wazony, Doniczki, Oświetlenie), Pomieszczenie (Dom, Ogród).

**3 · `holders-mounts` — Uchwyty i mocowania / Holders & Mounts**

- **Inclusion criterion:** the model exists to hold one specific object in a fixed position, or to attach something to a surface.
- **Positive examples:** phone and tablet stands, headphone hooks, wall brackets, VESA adapters, cable clips used as fixings, tool holders, remote-control mounts, car-vent mounts.
- **Boundary / non-examples:** a multi-compartment desk tray → **Przechowywanie i organizacja** (it sorts many things); a wall hook shaped like an animal → **stays here** — function wins over styling when the object is unusable without its fixing role; a bracket for a printer part → **Drukarka 3D i akcesoria** (printer-specific always wins).
- **Crosses tag groups:** Typ (Uchwyty, Klipsy), Pomieszczenie (Auto, Biurko, Łazienka), Zastosowanie (Naprawy).

**4 · `electronics-cables` — Elektronika i kable / Electronics & Cables**

- **Inclusion criterion:** the model houses, routes, protects or mounts electronics, wiring or connectors.
- **Positive examples:** project enclosures, PCB and board mounts, cable trays, cable wraps and routing clips, plug and adapter holders, LED diffusers, single-board-computer cases.
- **Boundary / non-examples:** a battery-powered decorative lamp → **Dekoracje i wystrój** (the electronics are incidental); a soldering third-hand → **Narzędzia i warsztat** (it is a tool for working *on* electronics, not a home for them).
- **Crosses tag groups:** Zastosowanie (Elektronika, Lutowanie), Typ (Etui, Klipsy, Oświetlenie), Pomieszczenie (Biurko).
- **Note:** this is the category that makes the packet's canonical `kabel` search example land somewhere sensible — a free-text `kabel` reaches models by name *and* by tag, and the `+tag Kabel` suggestion and this browse entry are visibly different offers.

**5 · `tools-workshop` — Narzędzia i warsztat / Tools & Workshop**

- **Inclusion criterion:** the model is a tool, jig, fixture or aid used while making, measuring or repairing something.
- **Positive examples:** soldering helping-hands, marking and drilling jigs, sanding blocks, bench aids, clamps, measuring aids, general test/calibration prints.
- **Boundary / non-examples:** a screw organizer → **Przechowywanie i organizacja**; a printer-specific calibration tower → **Drukarka 3D i akcesoria**; a replacement knob for a drill → **Części zamienne** (it restores an object rather than helping you work).
- **Crosses tag groups:** Zastosowanie (Naprawy, Lutowanie, Kalibracja), Typ (Uchwyty, Gadżety).

**6 · `printer-3d` — Drukarka 3D i akcesoria / 3D Printer & Accessories**

- **Inclusion criterion:** the model only makes sense to someone who owns a 3D printer — it upgrades, maintains or feeds the printer itself.
- **Positive examples:** K1 Max mods, spool holders, filament guides and dry-box parts, nozzle and tool trays, enclosure parts, printer-specific calibration towers.
- **Boundary / non-examples:** a generic caliper holder → **Narzędzia i warsztat**; an empty spool turned into a vase → **Dekoracje i wystrój**.
- **Crosses tag groups:** Drukarka (K1 Max, Akcesoria), Zastosowanie (Kalibracja), Materiał (PLA, PETG, PCTG, TPU).

**7 · `toys-games` — Zabawki, gry i figurki / Toys, Games & Figures**

- **Inclusion criterion:** the model's purpose is play, collecting, or display as a character or object of interest.
- **Positive examples:** articulated figures and flexi animals, puzzles, fidgets, board-game inserts and tokens, miniatures, pet toys.
- **Boundary / non-examples:** an abstract sculpture → **Dekoracje i wystrój** (it decorates a room, it is not a character); a board-game box insert → **stays here** — it belongs to the game, and a player looks for it under the game, not under storage. This is the one deliberate exception to criterion 1 of `storage-organization`, and it is recorded so a curator does not "fix" it.
- **Crosses tag groups:** Typ (Figurki ruchome, Gadżety), Pomieszczenie (Zwierzęta, Dom).

**8 · `replacement-parts` — Części zamienne / Replacement Parts**

- **Inclusion criterion:** the model replaces or repairs a broken or missing part of an existing manufactured object.
- **Positive examples:** appliance knobs and buttons, washing-machine feet, drawer runners, car trim clips, replacement handles, adapters that make an obsolete accessory fit again.
- **Boundary / non-examples:** a tool used to perform the repair → **Narzędzia i warsztat**; a printer replacement part → **Drukarka 3D i akcesoria** (printer-specific always wins); a generic hook you add where none existed → **Uchwyty i mocowania** (nothing is being restored).
- **Crosses tag groups:** Zastosowanie (Naprawy), Pomieszczenie (Auto, Kuchnia, Łazienka).

### Category ↔ Tag label collisions, and how each is resolved

Similar labels are permitted **only** with an explicitly recorded semantic distinction. Every category label below was deliberately widened so that **no category label is byte-identical to any shipped tag or tag-group label** — which gives Story 52.3's label-overlap check a known-good baseline instead of a fresh judgement call.

| Category label | Colliding shipped label | Resolution |
|---|---|---|
| Przechowywanie i **organizacja** | Tag `Przechowywanie` (Zastosowanie) | Category = the object **is** storage. Tag = the model is *used in* a storage context (e.g. a label holder). Widened by `i organizacja`. |
| Dekoracje **i wystrój** | Tag `Dekoracje` (Typ) | Category = the broad browse intent. Tag = the object's shape class. Widened by `i wystrój`. |
| Uchwyty **i mocowania** | Tag `Uchwyty` (Typ) | Category = holding **or** fixing, including brackets and adapters. Tag = the object is literally a handle/holder. Widened by `i mocowania`. |
| **Drukarka 3D** i akcesoria | TagGroup `Drukarka`, Tag `Akcesoria` | Category = things for the printer. TagGroup = *which* printer a model targets. Widened by `3D` + `i akcesoria`. |
| Elektronika **i kable** | Tag `Elektronika` (Zastosowanie) | Category = the object houses/routes electronics. Tag = the model is used *for* electronics work. Widened by `i kable`. |
| Zabawki, gry **i figurki** | Tag `Figurki ruchome` (Typ) | Distinct strings already; the category is the superset intent. |
| Części zamienne | Tag `Naprawy` (Zastosowanie) | Distinct strings. Category = the object **is** the replacement. Tag = the model participates in repair work. |
| Narzędzia i warsztat | — | No shipped collision. |

### Candidates considered and rejected

Recorded so a future curator does not re-propose them, and so the "do not generate categories 1:1 from TagGroup" finding stays visibly honoured.

| Rejected candidate | Why |
|---|---|
| `Kuchnia`, `Łazienka`, `Ogród`, `Auto`, `Biurko` (room-based) | A room is a *refinement* of any category, not a kind of thing. These already exist as the `Pomieszczenie` facet; promoting them would recreate the scope-vs-checkbox confusion this pass exists to remove. |
| `Gridfinity`, `Multiboard`, `Bin Shells` (system-based) | Each is a narrow ecosystem vocabulary and already a `System` tag. Fails admission test 1 and 3. |
| `PLA`, `PETG`, `TPU` (material) | Pure refinement — nobody browses "show me PETG things". |
| `Premium`, `Twórca` (provenance / level) | Provenance and tier, not a kind of thing. Belongs to facets, where it already lives. |
| A 1:1 lift of the `Typ` group (12 categories) | Object-shape granularity, not browse granularity. Twelve rows of `Wazony / Klipsy / Etui` reproduces the overloaded sidebar. Explicitly contradicted by the packet's research finding. |
| `Nowości`, `Popularne` | These are **sorts**, not categories. `sort` is already an independent URL layer. |
| `Inne` / `Pozostałe` catch-all | Zero categories is already valid and publicly visible; a catch-all would add a second, competing meaning for "uncategorised" and would attract lazy curation. The admin curation queue is the right home for the uncategorised set. |
| A `parent → child` starter tree | The schema may carry `parent_id`, but MVP browse is flat by decision `FR26-CAT-4`. Seeding a tree would ship UI-invisible structure that immediately drifts. |

### Open obligation (honest, not satisfied here)

`FR26-GOV-1` requires **evidence** that each category is a useful entry point for multiple models. This pass could **not** produce that evidence: the repository carries no local database, and live systems are out of scope for this run. What is supplied instead is a *derivation* — every category is justified against the shipped `STARTER_TAXONOMY` vocabulary and crosses ≥ 2 tag groups.

**Story 49.2 owes, before seeding:** a distribution check against the real catalogue confirming each of the eight would land ≥ 3 models under deliberate curation, and a documented reorder or merge for any that would not. This is a story-entry obligation, not a blocker on the set itself.

**No model assignments are produced by this pass** — models start uncategorised and are curated deliberately, exactly as Initiative 25 did with tags. **No automatic tag→category inference exists anywhere**, in this pass or in MVP.

## Voice and Tone

Microcopy only; brand posture lives in `DESIGN.md` § Brand & Style. Copy is en/pl with genuine Polish (never English-identical), and **entity labels are never i18n keys** — they come from `name_pl` / `name_en` with an `name_en` fallback when `name_pl` is null *or empty string*.

| Do | Don't |
|---|---|
| "Przeglądaj" / "Browse" | "Odkrywaj", "Eksploruj" — this is a private tool, not a storefront |
| "Szukaj w całym katalogu" / "Search entire catalog" | "Wyczyść" / "Clear" — it does not clear the query, and saying so would be a lie |
| "Filtry (3)" / "Filters (3)" | "Filtry (0)" — the badge is absent at zero, never shown as a zero |
| "Kategoria: Przechowywanie i organizacja" | "Wybrana kategoria: …" — the chip *is* the selection, no label needed |
| "Szukaj: kabel" / "Search for: kabel" (query row) | Rendering the query row with no verb, indistinguishable from a tag |
| "Dodaj filtr: Kabel, grupa Zastosowanie" (accessible name of a `+tag` row) | "Kabel" alone — the action is invisible to a screen reader |
| "Bez kategorii — do uzupełnienia" (admin only) | Showing that phrase to a regular member — a zero-category model is *normal* |
| "Zastąp kategorie" / "Replace categories" (admin save) | "Zapisz zmiany" / "Save changes" — it replaces a set, it does not merge |
| "Ta kategoria ma 2 modele" (advisory) | "Błąd: kategoria zbyt mała" — nothing in curation QA is an error |
| "Powiększ" / "Pomniejsz" / "Dopasuj" (viewer) | Icon-only zoom controls with no accessible name |

## Component Patterns

Behavioural. Visual specs live in `DESIGN.md` § Components.

| Component | Use | Behavioural rules |
|---|---|---|
| **Browse rail** | Desktop, `lg`+ | Renders "All catalog" then categories ordered `(position, slug)`. Each row is a `Link`; the whole row is the hit target. Never a checkbox. Selecting a row **replaces** the scope — it never adds a second one. Empty categories render dimmed but remain focusable and navigable. The rail is a `<nav>` with its own accessible name, distinct from the app's `ModuleRail`. |
| **Rail count** | Rail + Browse sheet | `model_count` from `GET /api/categories` — *not* filter-aware. It answers "how big is this category", never "how many match my current filters". A story must not silently make it reactive to `q`/`tag_ids`. Rendered inside the row's accessible name, so a screen reader hears label + count as one item. |
| **Browse sheet** | Below `lg` | Same rows, same semantics, one column. Opening it closes the Filters sheet. Selecting a row navigates **and** closes the sheet. Focus returns to the Browse trigger on close. |
| **Scope chip** | Any surface with an active scope | One per surface, full-width row above the grid. Not removable by a bare `×`. Carries the category label plus **one** trailing action whose label depends on state: **"Search entire catalog"** when `q` or any tag/status/source is active, **"Clear category"** when the scope is the only constraint. Never counted in `Filters (n)`. Never rendered when no scope is active. |
| **Search input + suggestion panel** | Catalog toolbar | ARIA 1.2 combobox: `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`; the panel is `role="listbox"`, rows are `role="option"`. Panel opens at ≥ 1 typed character, debounced. **Enter always runs the plain text query**, whatever is highlighted, unless the user has explicitly arrowed onto a `+tag` row — arrowing is an explicit act, typing is not. Escape closes the panel and keeps the text. |
| **Suggestion row — plain query** | Always row 1 | Fixed first position so `Enter` is predictable. Selecting it commits `q` and closes the panel. |
| **Suggestion row — `+tag`** | Rows 2…8 | Selecting it appends the canonical `tag_id` to `tag_ids`, **clears the typed text**, and closes the panel. One row per `tag_id`; a tag matched in the non-active locale renders the active-locale label plus a muted matched-alias hint. Group suffix resolves from the already-loaded `useTagGroups()` map; if the map is absent, the pill renders **without** a suffix — never a placeholder, never a blocking fetch. |
| **Suggestion overflow note** | When more tags matched than fit | Non-interactive, not a focus stop, not an `option`. Points at `Filters` as the exhaustive surface. It exists so the 8-row cap does not read as "these are all the matches". |
| **`Filters (n)` trigger** | Both regimes | `n` = selected `tag_ids` + `untagged` (1 if on) + `status` (1 if set) + `source` (1 if set). **`sort` is not counted** — it is an ordering, not a constraint. **`tag_match` is not counted** — it modifies an already-counted set. **Category is never counted.** Badge omitted entirely at `n === 0`. |
| **`Filters (n)` surface** | Sheet (compact) / panel (desktop) | One component, one state model, two presentations. Contains the relocated facet-group list verbatim — group search, collapsible groups, per-tag counts, the trailing `Bez tagów` row — then status, source, sort. Group collapse state stays in `localStorage` under the shipped key. Opening it closes the Browse sheet. |
| **Promoted group control** | Desktop only, ≤ 2, **off by default** | A group qualifies only if it has ≥ 2 tags with non-zero counts. Promoting a group does **not** remove it from the Filters surface — it is a shortcut, never a relocation, so the Filters surface stays exhaustive. |
| **Model-detail category list** | `/catalog/$modelId` | Renders in the *location* vocabulary, visually and semantically separated from `TagGroupsSection`. Each entry links to `/categories/{slug}`. A zero-category model renders **nothing at all** for members — no empty state, no placeholder; admins additionally see the curation affordance, mirroring the shipped 45.2 empty-group posture. |
| **Admin category row** | `/admin/categories` | Slug, both labels, position, `model_count`, inclusion criterion (truncated inline), row menu (rename / reorder / edit criterion / delete). Criterion is visible **in the list** because it is the admission test — an admin comparing two categories must see both criteria at once. |
| **Admin replace-set editor** | Per model | Re-fetches on open. Shows the last audited writer and timestamp. Save button reads **"Replace categories"**. Shows the advisory 1–3 warning inline when the pending set exceeds 3 — and **still allows the save**. Never implies merge or conflict detection: under the accepted last-writer-wins posture a concurrent edit is silently discarded, and the copy must not promise otherwise. |
| **Curation QA queue** | `/admin/categories` | Six advisory checks, each a row with a warning marker, the finding, the affected entity, and a link to the fix: (1) model with **zero** categories, (2) model with **> 3** categories, (3) **empty** category, (4) **tiny** category (`model_count` 1–2), (5) Category/Tag label collision, (6) ungrouped user-facing tag (`Tag.group_id IS NULL`). Every one is advisory — a warning row and a link, never a block. **No suggestion is ever auto-applied and no membership is ever inferred from tags.** |
| **Fullscreen image viewer** | Model gallery, share carousel | Modal dialog per WAI-ARIA APG: focus trap, `Escape` closes, focus returns to the trigger. Body scroll locked on open and **restored** on close. Zoom controls are **always mounted** and are never part of the tap-to-hide chrome layer. Toolbar lives **outside** the transform layer, so it never scales or translates with the image. |

## State Patterns

Every surface, every state. "Regular" means an authenticated non-admin member.

| State | Surface | Treatment |
|---|---|---|
| **Cold load** | Browse rail | Skeleton rows sized to the expected row height. The rail resolving is **independent** of the grid — a pending category list must never blank an already-painted grid. |
| **Cold load** | Result grid | Existing `LoadingState variant="skeleton-grid"`, unchanged. |
| **Cold load** | Suggestion panel | Panel does not open until there is at least one row to show. No spinner inside the panel, no empty flash. |
| **Empty** | A category with zero models | Grid empty state: "Nothing in this category yet." Primary action **"Search entire catalog"** — the same escape as the chip, so the dead end always has a door. |
| **Empty** | Scoped search with no hits | "No matches in {Category}." Primary action **"Search entire catalog"** (keeps `q` and tags, drops the scope). Secondary **"Clear filters"** (keeps the scope, drops the rest). Two different recoveries because two different things could be wrong. |
| **Empty** | Scoped + ≥ 2 tags + effective AND | The shipped AND-too-narrow branch still wins: primary **"Switch to OR"**, secondary **"Clear filters"**, and the scope survives both. Ordering matters — this branch is checked before the generic scoped-empty branch. |
| **Empty** | Suggestion panel, no tag matches | Panel still opens with **only** the plain-query row. Never a "no results" panel — the query row is always a valid offer. |
| **Empty** | `Filters (n)` surface, tag search with no match | Existing "no matches" copy inside the group list, unchanged. |
| **Empty** | Category list is empty (pre-seed) | Rail renders "All catalog" alone, no error, no empty-state copy. This is the true state between Story 49.1 and Story 49.2. |
| **Empty** | Model detail, zero categories | Members: nothing rendered. Admins: "Bez kategorii — do uzupełnienia" + link to assign. |
| **Empty** | Curation queue, nothing to flag | "Nothing needs attention." Not an error, not a celebration. |
| **Error** | Category read fails | Rail degrades to **"All catalog" + inline retry**; the grid stays fully usable. The catalogue must never become unreachable because a navigation aid failed. |
| **Error** | Model read fails | Existing full-surface `EmptyState tone="error"` + retry, unchanged. |
| **Error** | Tag suggestion read fails | Panel shows the plain-query row **only**. No error text — the user's action still works, so an error would be noise. |
| **Error** | Admin write fails | Existing `ApiError` toast/inline pattern. Delete of a category with assignments returns `409` and surfaces a **distinct** message naming the count and offering the explicit detach path — never a silent cascade, never a generic failure. |
| **Stale** | Admin replace-set editor | Re-fetch on open. If the server's set differs from the last-seen set, show a non-blocking note naming the last audited writer before the user edits. |
| **Unknown slug** | `/categories/{unknown}` | Empty page with `total = 0`, **not** a 404 — a stale bookmark degrades gracefully. The chip renders the raw slug and the escape action stays available. |
| **Loading (slow image)** | Viewer | Existing `catalog.image_viewer.loading` treatment. Zoom controls stay mounted but disabled until the image resolves; disabled state is announced, not just dimmed. |
| **Error (image)** | Viewer | Inline error inside the frame; close and toolbar remain reachable. **A failed image never traps the user.** |
| **Zoomed** | Viewer | Reset control becomes the affordance of record. Swipe navigation is suspended (see § Interaction Primitives); chevrons and the thumb strip remain the navigation path. |
| **Rotation** | Viewer, mobile | Re-fit to the new viewport, preserving zoom *level* but re-clamping pan. Never leaves the image outside the visible area. |

## Interaction Primitives

**Pointer / touch**

- Rail row, Browse-sheet row, scope chip action, suggestion row, filter row: single tap/click. No hover-only affordance anywhere in this pass — every action is visible at rest on touch.
- **Viewer gesture arbitration, stated normatively:**
  - at zoom scale **1.0** — a horizontal drag navigates (existing 50 px threshold, 60 px vertical tolerance, strip-origin drags never navigate);
  - at zoom scale **> 1.0** — a drag **always** pans and **never** navigates; navigation is available only via the visible chevrons, the thumb strip, or arrow keys;
  - **Reset** returns to 1.0 and re-arms swipe navigation;
  - double-tap toggles between 1.0 and a fixed zoom step; it is a convenience, and every state it reaches is also reachable by the visible controls.
- **No gesture is the only path to anything.** Pinch, pan and double-tap each have a visible single-pointer equivalent — this is `NFR26-A11Y-1` / WCAG 2.2 SC 2.5.1 and SC 2.5.7, not a preference.

**Keyboard**

- `Tab` order matches reading order on every surface: rail → toolbar (search, Browse, Filters) → scope chip → grid → pagination.
- Search combobox: `↓`/`↑` move `aria-activedescendant` through the rows; `Enter` commits the highlighted row; `Escape` closes and keeps the text; `Tab` closes and moves on without committing a tag.
- **`Enter` with nothing explicitly highlighted always runs the text query.** This is the mechanism behind "Enter never silently converts text into a tag".
- Sheets and the viewer: `Escape` closes, focus returns to the trigger, focus is trapped while open.
- Viewer: `←`/`→` navigate, `+`/`-` zoom, `0` resets. Every one of these also exists as a visible control.
- The rail is reachable by `Tab` and is not a focus trap; it does not steal focus on navigation.

**Banned everywhere in this pass**

- Internal scrollbars inside the suggestion panel.
- Hover-only reveals on any surface reachable below `lg`.
- Modal stacked on modal.
- Auto-widening the scope, auto-applying a curation suggestion, or inferring category membership from tags.
- `user-scalable=no` — under any circumstance.
- Changing the global `ModuleRail`.

## Accessibility Floor

Behavioural. Visual contrast targets live in `DESIGN.md` § Colors.

**WCAG 2.2 AA across every surface in this pass**, with three success criteria treated as hard acceptance rather than review notes:

- **SC 2.5.1 Pointer Gestures** — no path requires a multipoint or path-based gesture. Pinch and double-tap have visible button equivalents.
- **SC 2.5.7 Dragging Movements** — no path requires dragging. Pan has zoom-and-reset equivalents; image navigation has chevrons, thumbs and arrow keys.
- **SC 2.5.8 Target Size Minimum** — every interactive control introduced here is ≥ `{spacing.target-min}` (24×24 CSS px). The fullscreen close control is ≥ `{spacing.target-fullscreen-close}` (44×44), per the operator packet.

**The three-channel rule (load-bearing).** The plain-search action and the `+tag` action must be distinguishable by **three independent channels**, never by appearance alone:

1. **Glyph** — magnifier vs plus;
2. **Shape** — plain text vs a `{rounded.full}` pill carrying a group suffix;
3. **Accessible name** — "Szukaj: kabel" vs "Dodaj filtr: Kabel, grupa Zastosowanie".

Channel 3 is the one `NFR26-A11Y-1` names explicitly, and it is the one most easily lost in implementation — a story that ships the icon and the pill but leaves both rows named "Kabel" has **failed** this spine.

**Announcements**

- Result count changes announce via a polite live region on scope change, filter change and query commit — one region, not one per control.
- The rail's active row carries `aria-current="page"`.
- The scope chip is not a live region; the result count is. The chip is stable content the user can return to.
- Suggestion rows announce label, kind, and group. The overflow note is `aria-hidden` from the listbox and read as static text after it.
- Viewer zoom level changes announce politely ("200%"), because a zoom with no visual frame of reference is otherwise silent.

**Focus**

- Focus rings come from the shipped `{colors.ring}` token via the global `*:focus-visible` rule — no surface in this pass suppresses them.
- Every sheet, panel and dialog returns focus to its trigger on close.
- Navigating to a category moves focus to the results heading, not to the top of the document — a keyboard user must not have to re-traverse the rail after every selection.

## Responsive & Platform

| Breakpoint | Browse | Filters | Scope chip | Suggestions |
|---|---|---|---|---|
| `≥ lg` (1024px+) | Persistent left rail, `w-60` | Right panel/drawer | Full-width row above the grid | Popover under the input, width = input |
| `< lg` | `Sheet` from the left, opened from a toolbar **Browse** control | `Sheet` from the bottom | Same row, wraps to two lines if needed; the action never wraps away from the label | Panel pinned under the input, still ≤ 8 rows, still no internal scroll |

The Browse control and the Filters control sit **side by side** in one toolbar row below `lg`, with distinct labels and distinct icons. They are never merged into one sheet with tabs — that would re-merge the browse/refine distinction this initiative exists to separate.

The mobile bottom `ModuleRail` is **unchanged**. Adding a sixth tab is out of scope and is the `Ask First` boundary Story 48.1 drew and Story 51.3 repeats.

Safe-area insets and `dvh` (never `vh`) govern the viewer's height budget on phones, exactly as Story 48.1 established.

## Inspiration & Anti-patterns

Drawn from the packet's 18-source research registry.

- **Lifted from Printables / MakerWorld:** a short, stable, broad category vocabulary as the primary browse spine, with facets kept separate. ~6–10 categories scan in one glance; large hierarchies do not.
- **Lifted from Amazon:** attribute suggestions rendered as *explicit* `+` actions rather than as query rewrites. The user adds a constraint on purpose.
- **Lifted from Baymard (autocomplete):** keep the list short; make suggestion types visually and semantically distinct; never make the user scroll inside an autocomplete.
- **Lifted from Baymard (horizontal filtering):** promoted filters stay at 2–4 maximum; the full facet set belongs in a dedicated surface.
- **Lifted from Algolia (faceting):** active constraints must be visible regardless of where they were selected — hence the scope chip and the `Filters (n)` badge being complementary, never overlapping.
- **Lifted from WAI-ARIA APG:** the combobox pattern for suggestions and the modal-dialog pattern for the viewer, verbatim rather than re-derived.
- **Rejected — generating categories 1:1 from `TagGroup`:** explicitly contradicted by the research and by the operator decision. It would rebuild the overloaded sidebar with a new name.
- **Rejected — visually identical query / category / tag suggestions:** the research finding is that identical-looking suggestion types are missed or confused. Hence the three-channel rule.
- **Rejected — a category tree in the MVP browse UI:** depth exists in the schema at most; a tree in the rail is the same overload in a different shape.
- **Rejected — multi-select category scope:** two active scopes make the chip, the URL and the count all ambiguous, and the operator fixed one scope for the public MVP.
- **Rejected — a "did you mean the whole catalogue?" auto-widen:** silently changing the user's scope is the thing the visible chip exists to prevent.
- **Rejected — an `Inne` / `Other` catch-all category:** see § Browse Taxonomy, rejected candidates.

## URL and state transitions

The URL is the state model for every public surface in this pass.

| Layer | Where it lives | Notes |
|---|---|---|
| `category` | **path** — `/categories/{slug}` | One at a time. Slug, not UUID — first paint needs no resolve round-trip. |
| `q` | query | Free text. Tag-aware server-side; still just text on the wire. |
| `tag_ids` | query | Canonical UUIDs, deduped, validated by the shipped `UUID_RE` guard. |
| `tag_match` | query | Only meaningful and only persisted at ≥ 2 tags — shipped normalisation unchanged. |
| `untagged`, `status`, `source`, `sort`, `page` | query | Unchanged. |
| Filters panel open/closed, Browse sheet open/closed, rail scroll | **ephemeral, deliberately not in the URL** | Sharing a URL should share a *result set*, not someone else's open drawer. |
| Facet-group collapse | `localStorage`, shipped key | Unchanged. |

**Transition table.** Every row is normative; the two starred rows are the ones a naive implementation gets wrong.

| Action | `category` | `q` | `tag_ids` / `tag_match` | `status` / `source` / `sort` | `page` |
|---|---|---|---|---|---|
| Select a category (rail / sheet / detail link) | **replaced** | preserved | preserved | preserved | reset |
| Select "All catalog" | cleared | preserved | preserved | preserved | reset |
| ★ **"Search entire catalog"** (chip) | cleared | **preserved** | **preserved** | **preserved** | reset |
| "Clear category" (chip, no other constraint) | cleared | — | — | preserved | reset |
| Commit a plain query (`Enter` / query row) | preserved | replaced | preserved | preserved | reset |
| Select a `+tag` row | preserved | **cleared** | tag appended | preserved | reset |
| Toggle a tag in Filters | preserved | preserved | toggled | preserved | reset |
| Toggle `untagged` | preserved | preserved | preserved | preserved | reset |
| Change status / source / sort | preserved | preserved | preserved | changed | reset |
| ★ **"Clear filters"** (empty state) | **preserved** | cleared | cleared | cleared | reset |
| "Switch to OR" (empty state) | preserved | preserved | `tag_match = any` | preserved | reset |
| Paginate | preserved | preserved | preserved | preserved | changed |

★ The two starred rows encode the same principle from opposite directions: **the scope and the constraints are independent layers, and an escape from one must never silently discard the other.** The natural implementations — `navigate({ search: {} })` for "Search entire catalog", and a full reset for "Clear filters" — both violate it.

All navigations use `replace: true`, matching the shipped `CatalogList` behaviour, so filter fiddling does not fill the back stack. Selecting a **category** is the one exception: it is a genuine navigation and pushes, so browser Back returns to the previous category.

## Component ownership

Which story owns which surface, and against which shipped file. Every path is a **`VERIFY-AT-CREATE-STORY` anchor**, not an assertion about the tree at story time — the standing epic:47 action item requires a fresh trace when the story is created.

| Component | Owning story | Shipped anchor |
|---|---|---|
| Browse rail | 51.1 | new; occupies the column `modules/catalog/components/FacetSidebar.tsx` holds today |
| Browse sheet (compact) | 51.3 | new; `Sheet` pattern from `modules/catalog/routes/CatalogList.tsx` |
| `/categories/$slug` route + scope chip | 51.2 | new route (`routeTree` regeneration required); `routes/catalog/index.tsx` `validateSearch` is the pattern |
| `category` URL layer | 50.2 | `routes/catalog/index.tsx` |
| Types + hooks (`useCategories`, `useCategoryBySlug`) | 50.1 | `lib/api-types.ts`, `modules/catalog/hooks/` |
| Suggestion combobox | 50.3 | `modules/catalog/components/FilterRibbon.tsx` (search input + the `+tag` control it replaces) |
| `Filters (n)` surface | 52.1 | `FilterRibbon.tsx` + relocated `FacetSidebar.tsx` |
| Model-detail categories | 51.4 | `modules/catalog/components/TagGroupsSection.tsx` (sibling, visually distinct) |
| Admin category screen | 52.2 | `modules/admin/TagGroupsPage.tsx` + `modules/admin/AdminTabs.tsx` (new tab) |
| Curation QA queue | 52.3 | `modules/admin/DuplicateTagsPanel.tsx` is the closest advisory-panel precedent |
| Viewer chrome + zoom | 53.2 | `modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx`; library undecided (`G26-LIB`) |
| Viewer test contract | 53.3 | `apps/web/tests/visual/image-viewer-containment.spec.ts` stays green |
| Starter taxonomy seed | 49.2 | `apps/api/app/core/db/seed.py` `STARTER_TAXONOMY` is the shape precedent |

Each UI story owns, at its own merge gate, its `en.json` + `pl.json` keys with a key-set diff, its component-level a11y assertions, and its targeted pl-PL Playwright coverage with an explicit `toBeVisible()` before every screenshot. E54 audits **across** surfaces; it is never where this proof first appears.

## Non-goals

Recorded so this spine cannot be read as authorising them.

- **No lightbox library is chosen.** Everything in § Component Patterns and § Interaction Primitives for the viewer is a *contract* that all three scored options (Yet Another React Lightbox + Zoom, PhotoSwipe 5.4.x, extend the in-house viewer) must satisfy. `G26-LIB` stays open and is settled by Story 53.1 plus physical Android Chrome evidence.
- **No multi-select category scope.** One at a time in the public UI.
- **No child-category UI.** The schema may carry `parent_id`; MVP browse is flat, and there is never a third level.
- **No tag → category inference, synchronisation or suggestion UI.** Advisory only, and this pass ships no advisory suggestion.
- **No model→category assignments.** The starter seed creates categories only; models stay uncategorised until curated.
- **No categories on `ModelSummary` / list cards.** Adding them would mean a second per-page eager load for no rendered pixel.
- **No categories on the anonymous share surface.** `ShareModelView` is unchanged; the `NFR25-LEAKFENCE-1` negative share-DTO test stays as the fence.
- **No change to the global `ModuleRail`.**
- **No new `--color-*` token, no new font, no new radius, no new shadow.**
- **No promoted filter groups in MVP** — the ceiling (≤ 2, desktop only) is specified so 52.1 can enable them without a second UX pass, but `FR26-BROWSE-1`'s "only when justified" clause is not satisfied by any evidence available today.
- **No re-opening of Story 48.1.** Its geometry invariants are preserved verbatim; E53 builds on top.
- **No migration of `Viewer3DModal` or other shared `DialogContent` consumers.** Story 48.1's recorded residual risk stays deferred.
- **No change to `Tag.group_id`.** Single nullable FK, no Tag↔TagGroup M:N.

## Story-entry gates still open after this pass

| Gate | Status after this pass | Who closes it |
|---|---|---|
| `G26-UXGATE` | **closed** — this artifact is the required targeted UX pass | this pass |
| `G26-CAT-SET` | **closed** — eight categories with `FR26-GOV-1` payloads, ordering, distinction rule, rejected candidates | this pass, with the § Open obligation distribution check owed by 49.2 |
| `G26-MIGRATE` | open | Story 49.1 create+validate — additive/reversible `0020`, migration test pinning, single Alembic head |
| `G26-LIB` | open by design | Story 53.1 recommendation + physical Android Chrome evidence |
| `G26-DEVGO` | open, per story | `bmad-create-story` + `bmad-create-story:validate` + controller confirmation of that specific story |
| Story 52.3 threshold | inherited default supplied (`> 3`, tiny = 1–2) | Story 52.3 confirms or replaces it against real distribution |
| Story 49.2 distribution evidence | **owed** | Story 49.2, before seeding — see § Open obligation |

## Key Flows

### Flow 1 — Michał finds the drawer insert he printed last spring (desktop, Saturday morning)

Michał is the operator. He is at his desk on a 27″ monitor, and he knows the model exists but not what he called it.

1. He opens `/catalog`. The left rail shows **All catalog** (active) and eight categories with muted counts.
2. He clicks **Przechowywanie i organizacja**. The URL becomes `/categories/storage-organization`, the rail row takes the primary location treatment with `aria-current="page"`, and a scope chip appears above the grid: *Przechowywanie i organizacja · Clear category*.
3. The grid re-paints to the category's models. The `Filters (n)` badge is absent — the scope is not a filter, and the badge proves it.
4. He opens `Filters`, ticks **Gridfinity** under *System*. The badge reads **1**. The scope chip is unchanged; the chip's action label flips to **Search entire catalog**, because there is now a constraint worth carrying elsewhere.
5. Six models. Not the one.
6. **Climax:** he clicks **Search entire catalog**. The scope clears, the chip disappears, and the grid widens — but the Gridfinity tag is *still selected*, badge still **1**. He did not lose his work by widening his search, and the one screen element that changed is the one he acted on. The insert is on row two: he had filed it under Narzędzia i warsztat months ago.

*Failure path:* the category read fails. The rail collapses to **All catalog** plus an inline retry, the grid never blanks, and Michał can still search — the catalogue does not become unreachable because a navigation aid did.

### Flow 2 — Kasia looks for a cable clip on her phone (member, one-handed, on a tram)

Kasia is a member. She is holding her phone in one hand and does not know the tag vocabulary.

1. She opens the catalogue. Below the toolbar she sees two controls side by side: **Przeglądaj** and **Filtry**.
2. She taps the search field and types `kabel`.
3. The panel opens with **four** rows, no scrollbar: first *🔍 Szukaj: kabel*, then three `+` rows — *`+ Kabel · Zastosowanie`*, *`+ Organizery kabli · Typ`*, *`+ Cable management · Zastosowanie`* rendered as **Kabel** with a muted *cable management* alias beneath.
4. She hits **Enter** without touching the arrows. It runs the plain query — the text search — and returns models matching by name *and* by tag. Nothing silently became a filter.
5. Twenty-two results, too many.
6. **Climax:** she reopens the panel, this time taps the `+ Kabel · Zastosowanie` pill. The typed text clears, a tag chip appears, the `Filters` badge ticks to **1**, and the result set drops to eight — and the difference between "I searched for a word" and "I added a filter" was legible at the moment she chose, not afterwards. She taps **Przeglądaj**, picks **Elektronika i kable**, and the sheet closes onto a scoped, filtered, eight-item grid.

*Failure path:* the tag suggestion read fails. The panel opens with the plain-query row alone and no error text — her action still works, so an error message would be noise.

### Flow 3 — Michał adds a ninth category and finds out it was a bad idea (admin, evening)

1. He opens `/admin/categories`. Eight rows, each showing slug, both labels, position, count and its inclusion criterion inline.
2. He adds **Wazony / Vases**, criterion "Modele wazonów.", and saves.
3. He opens a model's category editor. It re-fetches, shows *last edited by Michał, 21:04*, and he ticks Wazony alongside its three existing categories. The inline advisory appears: *4 kategorie — sugerowana norma to 1–3.* The save button still reads **Zastąp kategorie** and is still enabled. He saves anyway; the write succeeds and an audit row records the resulting set.
4. He opens the curation queue.
5. **Climax:** three advisory rows are waiting. *Kategoria „Wazony" ma 1 model* (tiny). *Kolizja etykiet: kategoria „Wazony" / tag „Wazony"*. *Model „Wazon spiralny" ma 4 kategorie*. Nothing is blocked, nothing was auto-corrected, and the queue has told him — in warning amber, not destructive red — that his new category is behaving like a narrow tag. He deletes it. It has one assignment, so the delete returns `409` naming the count and offering the explicit detach; he confirms, and the detach and delete land in one audited transaction.

*Failure path:* he had two browser tabs open and saved the model's categories from a stale one. The second save wins and the first is silently discarded — the accepted last-writer-wins posture. The audit row carries the discarded set, so it is recoverable and attributable. Nothing in the UI ever claimed otherwise.

### Flow 4 — Kasia inspects an 8:1 panorama on the tram (mobile viewer)

1. She opens a model detail and taps the first gallery image. The viewer opens fullscreen, contained, with the close control top-right at 44×44 — Story 48.1's geometry, unchanged.
2. The photo is a print-bed panorama; at fit-width the label she wants is a smear.
3. She pinches. The image scales; the toolbar does not — it sits outside the transform layer, same size, same 40% scrim.
4. She drags. Because scale is above 1.0, the drag **pans**; it does not skip to the next photo.
5. **Climax:** she taps the image to hide the chrome so she can see the full frame. The counter, chevrons and thumb strip fade — **but Zoom in, Zoom out and Reset stay**. She is zoomed in, one-handed, with no keyboard, and the way back is still on screen. She taps **Dopasuj**, the image resets to 1.0, swipe navigation re-arms, and she swipes to the next photo.

*Failure path:* the next image 404s. An inline error renders inside the frame; the toolbar and the close control stay reachable. A broken image never traps her.

### Flow 5 — Tomek browses with a keyboard only (member, no pointer)

Tomek is a member with a motor-control limitation. He uses a keyboard and a screen reader; he has never used a pointer on this app.

1. He tabs from the top bar into the browse rail. The screen reader announces *"Przeglądaj kategorie, nawigacja"*, then *"Wszystkie modele"*, then *"Przechowywanie i organizacja, 34"* — label and count as one item, because the count is inside the accessible name.
2. He presses `Enter` on **Elektronika i kable**. Focus moves to the results heading — not back to the top of the document — and a polite live region announces *"11 modeli"*.
3. He tabs to the search field, types `kabel`, and arrows down. Row 1 announces *"Szukaj: kabel"*. Row 2 announces *"Dodaj filtr: Kabel, grupa Zastosowanie"*.
4. **Climax:** the two offers are distinguishable to him with the screen off. He did not need the magnifier glyph, the pill shape or the colour — the accessible name carried the whole distinction, and the `Enter`-runs-the-query rule means his muscle memory never adds a filter by accident. He presses `Enter` on row 2, the live region announces *"4 modele"*, and he tabs into the grid.

*Failure path:* he tabs past the suggestion panel instead of choosing. The panel closes, the typed text stays in the field, and no tag was added — `Tab` commits nothing.
