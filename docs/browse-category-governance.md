# Browse category governance

Living reference for the Initiative 26 **browse categories** — the admission criteria each
category is held to, the rule that separates a category from a tag, the periodic curation-QA
routine, and the accepted concurrency posture on category assignment.

**What this document governs.** Which models belong in which category, and why. It is the
written form of `FR26-GOV-1` (`_bmad-output/planning-artifacts/prd.md`): every category carries
a one-sentence inclusion criterion, positive and boundary examples, bilingual labels, and a
stable slug.

**What this document is not.** It is not the admin API reference (that is the OpenAPI surface
under `/api/admin/categories`), not the UX specification (that is the Initiative 26 UX spine),
and not a decision record — the eight-category set was decided elsewhere and is transcribed
here, not re-argued.

**Where the runtime source of truth lives.** The database, reachable through
`GET /api/admin/categories`, which returns each category's current `inclusion_criterion`
alongside the public keys. `apps/api/app/core/db/seed.py` is **not** the running source of
truth: `seed_browse_categories()` is create-if-absent keyed on `slug` and never updates an
existing row, so an admin rename, reorder or rewritten criterion wins permanently and is not
reflected back into the seed. Everything transcribed below is therefore the **as-seeded
baseline**; when this document and the live admin read disagree, the live read is current and
this document is stale.

## Category vs Tag — the distinction rule

A **category** answers *"what kind of thing is this?"* — one broad browse entry point a person
would name unprompted when looking for something. A **tag** answers *"what is true about
this?"* — a facet that refines a result set (material, room, system, printer, use).

Operationally:

- A category is a **browse scope**: at most one is active at a time on the public surface, and
  it renders as a scope chip rather than as another filter checkbox.
- Tags are **filters**: many at once, OR within a tag group and AND between groups.
- The two layers are **independent**. Assigning a category never adds a tag, assigning a tag
  never adds a category, and there is no automatic inference in either direction — anywhere.
- Membership is **many-to-many and optional**. A model may carry zero, one, or many categories.
  Zero is a valid, publicly visible state; only the admin surface flags it as needing curation.

The admission test for a proposed new category: it must be a *kind of thing*, not a refinement
of one. If the answer is a room, a material, a system vocabulary, a provenance tier or a sort
order, it is a facet — see § "Candidates considered and rejected".

## The eight categories

In `position` order. Labels are bilingual; the inclusion criterion is stored as **canonical
English only** — the entity carries exactly one such field and the approved source supplied the
criteria in English, so "bilingual" applies to the labels and not to the criterion. Criterion
sentences below are transcribed byte-exact from the seeded values.

### 0 · `storage-organization` — Przechowywanie i organizacja / Storage & Organization

- **Inclusion criterion:** The model's primary purpose is to hold, sort or tidy other objects.
- **Positive examples:** Gridfinity bins and baseplates, drawer inserts, desk and drawer
  organizers, stackable boxes, wall-mounted racks, tool caddies, screw-sorting trays.
- **Boundary / non-examples:** a decorative bowl that happens to collect keys → **Dekoracje i
  wystrój** (the reason it is chosen is how it looks); a phone stand → **Uchwyty i mocowania**
  (it positions *one* object, it does not tidy several); a plant pot → **Dekoracje i wystrój**
  (holds soil, but the browse intent is decor).
- **Crosses tag groups:** Typ (Pojemniki, Organizery), System (Gridfinity, Multiboard, Bin
  Shells), Zastosowanie (Przechowywanie, Wkładki), Pomieszczenie (Kuchnia, Biurko).

### 1 · `home-decor` — Dekoracje i wystrój / Home Decor

- **Inclusion criterion:** The model is chosen mainly for how it looks in a living space, not
  for a job it performs.
- **Positive examples:** vases, decorative lamps and lampshades, wall art and reliefs, plant
  pots and planters, seasonal ornaments, display pieces.
- **Boundary / non-examples:** an articulated dragon → **Zabawki, gry i figurki**
  (play/collectible intent dominates); a lamp mounting bracket → **Uchwyty i mocowania**; a
  kitchen container in a pleasant colour → **Przechowywanie i organizacja** (function dominates;
  colour is not an intent).
- **Crosses tag groups:** Typ (Dekoracje, Wazony, Doniczki, Oświetlenie), Pomieszczenie (Dom,
  Ogród).

### 2 · `holders-mounts` — Uchwyty i mocowania / Holders & Mounts

- **Inclusion criterion:** The model exists to hold one specific object in a fixed position, or
  to attach something to a surface.
- **Positive examples:** phone and tablet stands, headphone hooks, wall brackets, VESA adapters,
  cable clips used as fixings, tool holders, remote-control mounts, car-vent mounts.
- **Boundary / non-examples:** a multi-compartment desk tray → **Przechowywanie i organizacja**
  (it sorts many things); a wall hook shaped like an animal → **stays here** — function wins
  over styling when the object is unusable without its fixing role; a bracket for a printer part
  → **Drukarka 3D i akcesoria** (printer-specific always wins).
- **Crosses tag groups:** Typ (Uchwyty, Klipsy), Pomieszczenie (Auto, Biurko, Łazienka),
  Zastosowanie (Naprawy).

### 3 · `electronics-cables` — Elektronika i kable / Electronics & Cables

- **Inclusion criterion:** The model houses, routes, protects or mounts electronics, wiring or
  connectors.
- **Positive examples:** project enclosures, PCB and board mounts, cable trays, cable wraps and
  routing clips, plug and adapter holders, LED diffusers, single-board-computer cases.
- **Boundary / non-examples:** a battery-powered decorative lamp → **Dekoracje i wystrój** (the
  electronics are incidental); a soldering third-hand → **Narzędzia i warsztat** (it is a tool
  for working *on* electronics, not a home for them).
- **Crosses tag groups:** Zastosowanie (Elektronika, Lutowanie), Typ (Etui, Klipsy,
  Oświetlenie), Pomieszczenie (Biurko).

### 4 · `tools-workshop` — Narzędzia i warsztat / Tools & Workshop

- **Inclusion criterion:** The model is a tool, jig, fixture or aid used while making, measuring
  or repairing something.
- **Positive examples:** soldering helping-hands, marking and drilling jigs, sanding blocks,
  bench aids, clamps, measuring aids, general test/calibration prints.
- **Boundary / non-examples:** a screw organizer → **Przechowywanie i organizacja**; a
  printer-specific calibration tower → **Drukarka 3D i akcesoria**; a replacement knob for a
  drill → **Części zamienne** (it restores an object rather than helping you work).
- **Crosses tag groups:** Zastosowanie (Naprawy, Lutowanie, Kalibracja), Typ (Uchwyty, Gadżety).

### 5 · `printer-3d` — Drukarka 3D i akcesoria / 3D Printer & Accessories

- **Inclusion criterion:** The model only makes sense to someone who owns a 3D printer — it
  upgrades, maintains or feeds the printer itself.
- **Positive examples:** K1 Max mods, spool holders, filament guides and dry-box parts, nozzle
  and tool trays, enclosure parts, printer-specific calibration towers.
- **Boundary / non-examples:** a generic caliper holder → **Narzędzia i warsztat**; an empty
  spool turned into a vase → **Dekoracje i wystrój**.
- **Crosses tag groups:** Drukarka (K1 Max, Akcesoria), Zastosowanie (Kalibracja), Materiał
  (PLA, PETG, PCTG, TPU).

### 6 · `toys-games` — Zabawki, gry i figurki / Toys, Games & Figures

- **Inclusion criterion:** The model's purpose is play, collecting, or display as a character or
  object of interest.
- **Positive examples:** articulated figures and flexi animals, puzzles, fidgets, board-game
  inserts and tokens, miniatures, pet toys.
- **Boundary / non-examples:** an abstract sculpture → **Dekoracje i wystrój** (it decorates a
  room, it is not a character); a board-game box insert → **stays here** — it belongs to the
  game, and a player looks for it under the game, not under storage. This is the one deliberate
  exception to the `storage-organization` criterion, and it is recorded so a curator does not
  "fix" it.
- **Crosses tag groups:** Typ (Figurki ruchome, Gadżety), Pomieszczenie (Zwierzęta, Dom).

### 7 · `replacement-parts` — Części zamienne / Replacement Parts

- **Inclusion criterion:** The model replaces or repairs a broken or missing part of an existing
  manufactured object.
- **Positive examples:** appliance knobs and buttons, washing-machine feet, drawer runners, car
  trim clips, replacement handles, adapters that make an obsolete accessory fit again.
- **Boundary / non-examples:** a tool used to perform the repair → **Narzędzia i warsztat**; a
  printer replacement part → **Drukarka 3D i akcesoria** (printer-specific always wins); a
  generic hook you add where none existed → **Uchwyty i mocowania** (nothing is being restored).
- **Crosses tag groups:** Zastosowanie (Naprawy), Pomieszczenie (Auto, Kuchnia, Łazienka).

**Zero-margin monitoring item — `replacement-parts`.** The admission bar for the set was that
each category would land **at least three** models under deliberate curation. `replacement-parts`
clears that bar at **exactly three**. It therefore stays, unchanged and un-merged, and is
registered as a standing tiny-category monitoring item: it is the one row that will surface in
the QA panel's tiny-category check first, and the one a curator might otherwise be tempted to
"fix" by merging it away. Any later merge or retirement is admin governance, never a re-seed.

**Evidence provenance, and its limit.** The distribution check behind that bar was run once,
read-only, against the live catalogue, and analysed twice independently (a full curation pass and
an adversarial falsification attempt), both agreeing that every category clears the bar. The
capture and both reports are **local and gitignored** — they are **not reproducible from this
repository**. The test suite runs against an empty scratch database with no access to the real
catalogue, so the dataset tests are a post-decision drift guard and nothing more.

## Category ↔ Tag label collisions, and how each is resolved

Similar labels are permitted **only** with an explicitly recorded semantic distinction. Every
category label was deliberately widened so that no category label is byte-identical to any
shipped tag or tag-group label, which gives the curation-QA label-overlap check a known-good
baseline instead of a fresh judgement call.

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

## Candidates considered and rejected

Recorded so a future curator does not re-propose them, and so the "do not generate categories
1:1 from TagGroup" finding stays visibly honoured.

| Rejected candidate | Why |
|---|---|
| `Kuchnia`, `Łazienka`, `Ogród`, `Auto`, `Biurko` (room-based) | A room is a *refinement* of any category, not a kind of thing. These already exist as the `Pomieszczenie` facet; promoting them would recreate the scope-vs-checkbox confusion this layer exists to remove. |
| `Gridfinity`, `Multiboard`, `Bin Shells` (system-based) | Each is a narrow ecosystem vocabulary and already a `System` tag. |
| `PLA`, `PETG`, `TPU` (material) | Pure refinement — nobody browses "show me PETG things". |
| `Premium`, `Twórca` (provenance / level) | Provenance and tier, not a kind of thing. Belongs to facets, where it already lives. |
| A 1:1 lift of the `Typ` group (12 categories) | Object-shape granularity, not browse granularity. Twelve rows of `Wazony / Klipsy / Etui` reproduces the overloaded sidebar. |
| `Nowości`, `Popularne` | These are **sorts**, not categories. `sort` is already an independent URL layer. |
| `Inne` / `Pozostałe` catch-all | Zero categories is already valid and publicly visible; a catch-all would add a second, competing meaning for "uncategorised" and would attract lazy curation. The admin curation queue is the right home for the uncategorised set. |
| A `parent → child` starter tree | The schema may carry `parent_id`, but MVP browse is flat by decision `FR26-CAT-4`. Seeding a tree would ship UI-invisible structure that immediately drifts. |

## Hierarchy — flat product, depth-2 schema affordance

Two separate statements, deliberately not conflated:

- **The product rule (`FR26-CAT-4`).** Browse is **flat**: roughly 6–10 broad categories, no
  child level rendered in MVP. A child-category UI ships only if real catalogue distribution
  demonstrates the need.
- **The schema affordance.** `browse_category` carries a nullable `parent_id`, so the storage
  layer *can* express one level of nesting. The **maximum product depth is 2** (root + child),
  exactly one parent per category, and never a DAG. There is never a third level.

**Which layer enforces it.** The depth-2 ceiling is enforced in the **service layer**, not in
DDL — SQLite cannot express it as a constraint. The admin governance routes reject a violating
write with `422` and a named error: `self_cycle`, `parent_not_root` (the proposed parent is
itself a child), or `reparent_exceeds_depth` (the category being moved has children, so the move
would push them to depth 3). A doc or UI that presents this as a database constraint is wrong
about where the guarantee lives.

## Periodic curation QA

The QA routine is **not** a manual procedure. It is the shipped curation-QA panel on
**`/admin/categories`**, which computes every check live. This section is the operating
instructions for that panel: how to read each row, what action each implies, and how often to
look.

The panel renders its checks in a **fixed order**:

| # | Check | What it means | Action it implies |
|---|---|---|---|
| a | **Empty categories** (`model_count == 0`) | A category nothing has been assigned to. Expected shortly after seeding; a standing signal otherwise. | Curate models into it, or — if the category has no plausible members in this catalogue — retire it through admin governance. Never by editing the seed. |
| b | **Tiny categories** (`1 ≤ model_count ≤ 2`) | The category is behaving like a narrow tag. This is the exact complement of the "≥ 3 models" admission bar. | Curate more models in, or reconsider whether the concept is a facet rather than a category. `replacement-parts` sitting at exactly 3 is *not* flagged here, but it is one assignment away from being flagged — see its monitoring note above. |
| c | **Label collisions** | A category label and a tag label read as near-identical after normalisation. | Resolve by widening one label and recording the semantic distinction in the collision table above — or confirm it is one of the already-recorded, accepted pairs. |
| d | **Over-categorized models** (`category_count ≥ 4`) | A model carries more categories than the advisory 1–3 norm. | Open the replace-set editor for that model and trim it — **or decide it is fine**. See the norm rule below. |
| e | **Uncategorized models** (a count) | How many models carry zero categories. Sourced from `GET /api/models?uncategorized=true`. Note the filter is a pure **AND**: combined with `untagged` it means *no tags AND no categories*, never a union. | Work the admin curation queue on the same page. This is a backlog figure, not a defect count. |
| f | **Ungrouped tags** (a count) | Tags with no `tag_group`. Facet-layer hygiene rather than category hygiene, but it lives on the same panel. | Assign the tags to groups on the tag-groups page. |

**Two rules the panel encodes, which no curator should override by habit:**

- **The 1–3 category norm is a warning and never an error.** There is no hard database maximum
  and no write-blocking enforcement anywhere. Assigning a fourth category succeeds; the editor
  warns and still saves. Check (d) raises an advisory finding, not a failure.
- **Zero categories is a valid, publicly visible state.** An uncategorized model appears in
  `GET /api/models` and renders normally on every user-facing surface. Check (e) exists to
  *curate* that set, not to flag it as broken.

**Cadence — event-driven, with a calendar backstop.**

- **Binding cadence: after every import batch.** Every one of the six checks is a
  curation-drift signal, and curation drift is caused by catalogue movement, not by the calendar.
  A batch of new models is what creates uncategorized rows, pushes a tiny category over the bar,
  or introduces a colliding tag label — so the batch, not the date, is the right trigger.
- **Backstop: monthly**, explicitly labelled as a backstop. A pure calendar cadence would fire
  six no-op checks in a month with no imports and miss a forty-model batch landing on day two;
  the monthly pass exists only to catch drift from small, unbatched edits.
- **Nothing automates either cadence.** No job, no cron, no alert watches these checks. The
  panel computes on load and only when someone opens it.

## Concurrency posture on assignment — accepted last-writer-wins

Category assignment is `PUT /api/admin/models/{model_id}/categories`: **replace-set**, the whole
set in one idempotent call, **explicit last-writer-wins**. Replace-set was chosen because the
admin UI edits a set, so it matches the actual edit unit and avoids partial-merge surprises.

**Last-writer-wins does permit a lost update.** If admin A and admin B both load a model's
categories, A adds `lamps` and saves, then B — still working from the pre-A snapshot — adds
`kitchen` and saves, **A's change is silently discarded**, because B's payload never contained
it. Replace-set does not prevent this; it only makes the discarded state a whole set rather than
a partial merge.

**Why it is accepted.** Not because the race is absent — it is not. Every write already emits an
audit row carrying the resulting set, so a lost update is **recoverable and attributable after
the fact** rather than invisible. For the current single-admin deployment that trade is
deliberate and explicit.

**The named trigger that ends the acceptance.** The moment a **second concurrent admin editor**
exists, or an **automated / agent writer** is added, this needs optimistic concurrency: a
`revision` integer or an ETag / `If-Match` precondition returning `409` on a stale write. Until
that trigger fires, no revision column and no precondition header is built. Any UI over this
endpoint must not imply merge or conflict-detection semantics it does not have.

## References

- `docs/architecture.md` — where browse categories sit in the system, and what the retired
  Initiative 25 taxonomy was.
- `docs/agents-add-model-runbook.md` — the agent-facing category contract (read-only; the
  import flow leaves models uncategorized).
- `apps/api/app/core/db/seed.py` — `STARTER_BROWSE_CATEGORIES`, the as-seeded baseline
  transcribed above.
- `apps/api/app/modules/sot/browse_category_admin_router.py` — the admin governance and
  replace-set assignment routes.
- `_bmad-output/planning-artifacts/prd.md` — `FR26-CAT-2` (many-to-many, zero valid),
  `FR26-CAT-3` (advisory norm), `FR26-CAT-4` (flat MVP, depth-2 ceiling), `FR26-GOV-1`
  (admission criteria).
