# Reconciliation — operator packet (`/tmp/3d-portal-init26-correct-course-input.md`)

Every UX-bearing statement in the packet, and where it landed. "Out of pass" means the statement is real and approved but belongs to a story or an artifact other than this spine pair.

## Scope B — search and suggestions

| Packet statement | Landed |
|---|---|
| Typed text remains ordinary `q`; Enter never silently converts text into a tag | `EXPERIENCE.md` § Component Patterns (search combobox), § Interaction Primitives (Enter rule), Flow 2 step 4, Flow 5 step 4 |
| Detect matching tags across PL+EN, show visually distinct pills `+ Kabel · Zastosowanie` | § Component Patterns (`+tag` row), `DESIGN.md` § Components (`suggestion-row-tag`, `suggestion-tag-pill`, `suggestion-group-suffix`) |
| Click stores canonical `tag_id`, deduplicated by ID across bilingual labels | § Component Patterns (`+tag` row) — one row per `tag_id` |
| Render active-locale label, optional subtle matched alias | § Component Patterns; `DESIGN.md` `{components.suggestion-alias}` |
| Autocomplete maximum 6–8 combined items, no internal scrollbar | § Component Patterns (8 hard, query row occupies slot 1 ⇒ ≤ 7 tags); `DESIGN.md` — panel has no `max-h`, `overflow: visible`; Do's and Don'ts |
| Ordinary search and `+tag` must have distinct semantics / appearance / a11y | § Accessibility Floor — the **three-channel rule**, with channel 3 (accessible name) called out as the one most easily lost |
| Keep `q`, category scope, `tag_ids`, `tag_match`, `sort` as independent visible URL state layers | § URL and state transitions |
| Remove reliance on the separate tiny `+tag` control, preserve a discoverable full Filters surface | § Component Ownership (50.3 replaces the `FilterRibbon.tsx:99-113` control), § Component Patterns (`Filters (n)` surface stays exhaustive) |

## Scope C — browse categories

| Packet statement | Landed |
|---|---|
| Left desktop navigation shows only broad categories and optional counts | § Component Patterns (Browse rail); `DESIGN.md` § Components |
| Mobile gets a separate Browse surface/menu | § Responsive & Platform; § Component Patterns (Browse sheet) |
| Active category shown as browse scope above results, not a checkbox, not in Filters count | § Component Patterns (Scope chip), § Component Patterns (`Filters (n)` trigger — normative count definition) |
| One active category scope; a model may appear on many category pages | § Foundation table; § Non-goals (no multi-select) |
| URL `/categories/{stable-slug}`; q/tags/sort remain query params | § URL and state transitions |
| Search started in category stays scoped, visible chip, one-click "Search entire catalog" | § Component Patterns (scope chip's two action labels), § URL transition table ★ row, Flow 1 climax |
| Tags/facets move to `Filters (n)`; optional 2–4 promoted groups only if justified; full tag search inside Filters | § Component Patterns (Filters surface, Promoted group control ≤ 2, **off by default**), § Non-goals |
| OR within one TagGroup, AND between TagGroups; category never mixed into `tag_match` | § Foundation, § URL and state transitions |
| ~6–10 broad categories, flat MVP, schema depth ≤ 2 | § Browse Taxonomy — **eight** categories, flat |
| Governance: criterion, positive + boundary examples, bilingual labels, stable slug, multi-model evidence | § Browse Taxonomy — per-category governance record; **multi-model evidence is an honest open obligation**, see below |
| Periodic QA: zero / unusually many categories, empty / tiny categories, tag-like categories, label overlap, ungrouped tags | § Component Patterns (Curation QA queue — six checks, thresholds supplied) |
| Similar labels only with explicit semantic distinction; no automatic sync or inference | § Browse Taxonomy — collision table; § Non-goals |

## Scope A — viewer

| Packet statement | Landed |
|---|---|
| Pinch zoom, pan, double-tap, **visible** Zoom In/Out/Reset | § Component Patterns (viewer), § Interaction Primitives; `mockups/key-viewer-chrome.html` frames A–C |
| Stable toolbar outside the transform layer | § Component Patterns; `DESIGN.md` § Elevation & Depth |
| Body lock, focus trap / return focus, safe area / dynamic viewport | § Component Patterns, § Accessibility Floor, § Responsive & Platform |
| Gesture conflict rules | § Interaction Primitives — normative scale-1.0 vs scale->1.0 arbitration |
| ≥ 44×44 close, ≥ 24×24 controls | `DESIGN.md` `{spacing.target-fullscreen-close}` / `{spacing.target-min}`; § Accessibility Floor |
| Library adoption not pre-decided | § Non-goals — first entry; the mock is explicitly library-agnostic |

## Deliberately **not** carried into this spine pair

These are real packet content that this pass does not own. None is dropped; each has a named home.

| Packet content | Why not here | Where it lives |
|---|---|---|
| The full Pixel-5 / panorama / rotation / repeated-open-close **test contract** | A test contract is not a UX decision | Story 53.3 |
| "Physical Android Chrome smoke required; synthetic Playwright touch is regression evidence only" | Evidence policy, not experience design | Story 53.3, gate `G26-LIB` |
| Backend `q` semantics — membership predicate, no count inflation, soft-delete, composition | Data contract | `architecture.md` Decision AY, Story 49.4 |
| `category` / `model_category` table shape, indexes, delete policy, migration strategy | Schema | `architecture.md` Decisions AX / AZ, Story 49.1 |
| `Tag.group_id` stays a single nullable FK | Already a closed decision; this spine only **preserves** it | `prd.md` § Initiative 26 Decisions; echoed in § Non-goals |
| "No additional operator questions are needed…" | Process instruction, honoured by running Fast path | `.memlog.md` entry 2 |

## Dropped qualitative ideas — surfaced, not buried

1. **"optional 2–4 promoted groups"** — the packet permits up to four. This pass caps at **two**, desktop only, and ships them **off**. The reduction is deliberate: `FR26-BROWSE-1` says "only when justified", and no evidence available today justifies any. The ceiling is written down so Story 52.1 can enable them without a second UX pass. If the operator wants four, that is a one-line change to `EXPERIENCE.md` § Component Patterns, not a redesign.
2. **"schema may include nullable `parent_id`"** — carried as schema-only. No child-category UI is designed, so a future depth-2 rollout will need a small UX increment. Recorded in § Non-goals rather than pre-designed, because designing a UI for a distribution nobody has measured is exactly the overload this initiative is undoing.
3. **"optional suggestions may be advisory only"** (tag→category) — the packet permits an advisory suggestion surface. This pass ships **none**. Reason: the curation queue already surfaces the same signal as a human-readable finding, and an advisory inference chip is one careless click away from becoming automatic. Recorded in § Non-goals with the packet's own "advisory only" wording preserved so the option stays open.
4. **`FR26-GOV-1` multi-model evidence** — the packet requires evidence that each category is a useful entry point for multiple models. **This pass could not produce it**: no local database in the repository, and live systems are out of scope. What is supplied is a derivation against the shipped `STARTER_TAXONOMY` (every category crosses ≥ 2 tag groups). The distribution check is recorded as an explicit obligation on Story 49.2 in `EXPERIENCE.md` § Open obligation. **This is a stated gap, not a satisfied requirement.**
