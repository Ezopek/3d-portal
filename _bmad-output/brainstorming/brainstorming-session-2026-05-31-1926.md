---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: ['_bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md', '_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md']
session_topic: 'STL slicer estimate profile resolver + slicer-worker architecture discovery (pre-PRD)'
session_goals: '(1) Lock the problem statement and non-goals for per-STL slicer estimates before any PRD; (2) Sketch the data model and ownership topology for PrintIntentPreset vs SlicerProfileBundle, material classes, Spoolman linkage, estimate records, profile hashes, and source-profile snapshots; (3) Define the profile-resolver architecture (Orca inheritance merge, validation, hashing/versioning, custom Spoolman-mapped overrides, import/export boundaries) grounded in the proven temporary resolver; (4) Define the slicer-worker architecture (container/runtime boundary, job IO, STL cache, g-code metadata parsing, failure/warning classification, queue/recompute behavior); (5) Specify estimate-invalidation rules and recompute triggers; (6) Separate MVP from gated/future capability, explicitly gating adaptive/variable layer height; (7) Record open decisions, risks, and the next BMAD step so downstream bmad-correct-course routing has unambiguous ground. Implementation planning remains BLOCKED until this artifact is verified.'
selected_approach: 'AI-recommended progressive flow (architecture-discovery emphasis)'
techniques_used: ['First Principles Thinking', 'Morphological Analysis', 'Constraint Mapping', 'What If Scenarios', 'Reverse Brainstorming', 'Pre-Mortem']
ideas_generated: 71
context_file: ''
workflow_completed: true
autonomous_facilitation: true
---

# Brainstorming Session Results

**Facilitator:** Ezop (autonomous; operator absent — facilitation is AI-driven per parent-controller directive "do not modify application code; this is architecture/brainstorming documentation only; record assumptions and unknowns")
**Date:** 2026-05-31

## Session Overview

**Topic:** STL slicer estimate profile resolver + slicer-worker architecture discovery (pre-PRD).

**Goals:**

1. Lock the problem statement and non-goals for **per-STL** slicer estimates before any PRD is written.
2. Sketch the data model and ownership topology for the user-facing `PrintIntentPreset` vs the internal `SlicerProfileBundle`, generic material classes, Spoolman linkage, estimate records, profile hashes, and source-profile snapshots.
3. Define the profile-resolver architecture — Orca inheritance merge, validation, hashing/versioning, custom Spoolman-mapped overrides, and the import/export boundary — grounded in the **proven** temporary resolver.
4. Define the slicer-worker architecture — container/runtime boundary, job inputs/outputs, STL cache paths, g-code metadata parsing, failure/warning classification, and queue/recompute behavior.
5. Specify estimate-invalidation rules and recompute triggers.
6. Separate MVP scope from gated/future capability, **explicitly gating adaptive/variable layer height**.
7. Record open decisions, risks, and the next BMAD step cleanly so the downstream `bmad-correct-course` step has unambiguous starting ground.

### Context Guidance

This session runs in **autonomous facilitation mode**. Operator (Michał) is not in the loop. Standard step-by-step user prompts in the `bmad-brainstorming` skill are skipped; the facilitator records assumptions inline (tagged `**Assumption:**`) and open decisions inline (tagged `**Open decision:**`) rather than asking the operator to resolve them. The downstream `bmad-correct-course` → PRD cycle is the right place to convert those into operator-confirmed decisions.

This is **architecture/brainstorming documentation only**. No application code is modified. No PRD is written. No epic, story, or sprint-status row is created. The artifact's job is to harden the technical ground (already partially proven via CLI feasibility spikes) so the PRD/architecture phase starts from a known-good baseline rather than blue-sky.

**Routing note (why a brainstorming artifact and not an `architecture.md` H2 append):** per AGENTS.md § Workflow expectations and § BMAD vanilla-first, `architecture.md` is the gated **phase-3 (solutioning)** output that follows a PRD. The slicer initiative has **no PRD yet** — it is in **phase-1 (analysis/discovery)**. Appending a full architecture section to `architecture.md` ahead of a slicer PRD would jump the phase order and is treated as a vanilla-first drift. The phase-correct, closest-to-vanilla home for pre-PRD architecture discovery is a brainstorming/discovery artifact in `_bmad-output/brainstorming/` (the same path the 2026-05-29 Spoolman discovery used). The architecture-doc content sketched here is captured as **inheritance notes** for the eventual architecture H2 append, not as the architecture doc itself.

### Verified facts in force at session start (controller-supplied; treat as ground truth)

These are **proven** via CLI feasibility spikes on Fenrir WSL, not assumptions. They are the spine of this artifact.

**Scope (load-bearing):**

- Scope is **per-STL estimates only**. A request/basket total is a **linear sum** of per-STL estimate × quantity. There is **no whole-basket / whole-plate slicing** in the MVP.
- The portal is a **printer/admin tool and a friends-&-family request assistant**, *not* e-commerce. No checkout, no payment, no public pricing engine. "Cost" is an informational owner-side figure (filament cost from the slice), not a quote.

**Runtime / environment:**

- Fenrir `.100` WSL SSH works. Windows user path is `/mnt/c/Users/ezope`.
- Orca Windows install exists at `/mnt/c/Program Files/OrcaSlicer/orca-slicer.exe`, but running the **Windows exe from WSL is not preferred**.
- Linux OrcaSlicer AppImage **v2.3.2** is installed on Fenrir WSL: `/home/ezop/tools/orcaslicer/OrcaSlicer_Linux_AppImage_Ubuntu2404_V2.3.2.AppImage`, with deps installed: `libopengl0`, `libglu1-mesa`, `libgtk-3-0`, `libwebkit2gtk-4.1-0`, `libsecret-1-0`, `libgstreamer-plugins-base1.0-0`, `libmspack0`.
- **Fenrir is a research/export source only — NOT a production runtime.** Production MVP runs Orca in a containerized slicer-worker (or an existing worker container). No production dependency on Fenrir's `.100` WSL host.

**Profile source data:**

- Current Orca user profiles: `/mnt/c/Users/ezope/AppData/Roaming/OrcaSlicer/user/default/{machine,filament,process}`.
- Raw Orca user-profile JSON files are **partial** and **cannot** be passed directly to `--load-settings` / `--load-filaments` because they lack a top-level `type`; `--datadir` does **not** fix this.
- A temporary resolver proved feasibility: `/home/ezop/tmp/orca_resolve_profiles.py` recursively merges system inherited profiles from `/mnt/c/Program Files/OrcaSlicer/resources/profiles` with the user partials, adds `type`, drops the problematic instantiation, and outputs full machine/process/filament JSONs **accepted by the Orca CLI**.

**Proven slices (Qstool.stl):**

- Sample `Qstool.stl`: `/mnt/c/Users/ezope/Downloads/Qstool.stl`. Orca `--info` reports size 105×130×125, manifold yes, facets 15834, volume 103018.2.
- **PLA slice works:** resolved Creality K1 Max MicroSwiss HF + Rosa3D PLA Starter + 0.20 mm process ⇒ 76.76 g, 61.90 cm³, 25735.79 mm, estimated time 3h35m47s, cost 4.60, warning *floating cantilever*.
- **TPU slice works:** resolved AI Rosa3D Flex 96A Black + AI 0.20 mm TPU FlowTech ⇒ 77.25 g, estimated time 8h06m05s, `filament_max_volumetric_speed` 2.8.

**G-code metadata (parseable lines confirmed present):**

- `; filament used [mm]`, `; filament used [cm3]`, `; filament used [g]`, `; total filament used [g]`, `; total filament cost`, `; estimated printing time (normal mode)`, `; filament_settings_id`, `; print_settings_id`, `; printer_settings_id`.

**Adaptive layer height (negative result — gate it):**

- Quick test: setting `adaptive_layer_height=1` in the resolved process did **NOT** change the layer-Z schedule or the estimates vs fixed 0.20 mm for Qstool. Treat automatic adaptive layer height as **unproven / gated**, likely requiring GUI / project layer-height data or deeper research before it can be relied on.

**Inventory linkage (inherited from the 2026-05-29 Spoolman discovery):**

- **Spoolman remains the source of truth for inventory** and for the `filament.extra.url` purchase link. The slicer initiative consumes Spoolman filament records; it does not own or duplicate inventory.

---

## 1 — First Principles: Problem statement & non-goals

### Problem statement

Given an STL and a small, user-chosen "how do I want this printed" intent (material class, quality tier, optional overrides), produce a **trustworthy, reproducible per-STL estimate** — print time, filament mass (g), filament length (mm), filament volume (cm³), informational filament cost, and any slicer warnings — by running a real OrcaSlicer slice headless, parsing the g-code metadata, and caching the result keyed to the exact inputs so it only recomputes when something that affects the estimate actually changes.

The estimate must be:

- **Reproducible** — same STL + same resolved profile bundle ⇒ same numbers. Achieved by hashing the resolved inputs and snapshotting the source profiles.
- **Attributable** — every estimate record names which printer/filament/process settings produced it (`*_settings_id` lines exist in the g-code for exactly this).
- **Invalidatable** — when the STL, the resolved bundle, the Orca version, or a mapped Spoolman override changes, the estimate goes stale and is queued for recompute rather than silently served wrong.

### Why per-STL (first-principles justification)

- A request is a **set of (STL, quantity)** lines. Owner-side decision-making needs "how long / how much filament for *this part*", which composes linearly to a basket total. Whole-plate slicing introduces packing/arrangement as a variable, multiplies the input space, and produces a number that does **not** decompose back to per-part attribution — wrong tool for a friends-&-family request assistant.
- Per-STL estimates are **cacheable and reusable** across requests; a whole-basket slice is bespoke to one basket and throws away on the next.

### Non-goals (MVP)

1. **No whole-basket / whole-plate slicing.** Totals are `Σ (per-STL estimate × qty)`.
2. **No e-commerce.** No checkout, quoting engine, public pricing, or payment. Cost is informational, owner-facing.
3. **No production dependency on Fenrir.** Fenrir is the research/export bench only.
4. **No adaptive / variable layer height** in the resolved process (gated — see §6, proven negative result).
5. **No Orca GUI in production.** Headless CLI only.
6. **No inventory ownership.** Spoolman stays source of truth; the portal mirrors/links, does not duplicate (inherited HC from the Spoolman discovery).
7. **No multi-printer optimization / printer auto-selection.** The intent preset (or its default) names the machine; the resolver does not "shop" for the fastest printer.
8. **No support-generation tuning UI / per-model mesh repair.** Manifold/repair is an input-validation concern (Orca `--info` already reports manifold), not an MVP feature.

---

## 2 — Data model & ownership sketch

> Sketch only. Field names are candidates for the PRD/architecture phase to confirm, not a migration spec. The ownership boundaries (who is source of truth) ARE load-bearing.

### 2.1 `PrintIntentPreset` (user-facing)

The small, human-meaningful "how I want this printed" object the requester/owner picks. Deliberately thin.

| Field | Type | Notes |
|---|---|---|
| `id` | pk | |
| `name` | str | e.g. "PLA – standard 0.20", "TPU – flexible part" |
| `material_class` | enum | `PLA` \| `PETG` \| `PCTG` \| `TPU` (TPU == Rosa Flex family) — see §2.3 |
| `quality_tier` | enum | candidate: `draft`/`standard`/`fine` mapping to a process (layer height) — confirm in PRD |
| `printer_ref` | fk → machine | which machine profile (default machine if unset) |
| `notes` | str | free text shown to requester |
| `is_default` | bool | one default per material class |

**Ownership:** portal owns `PrintIntentPreset` entirely. It is the **stable user-facing contract**; it must NOT leak Orca internals (no raw layer-height floats, no `filament_max_volumetric_speed` in the UI). The mapping from preset → concrete Orca settings lives in `SlicerProfileBundle`, deliberately separated so Orca version churn / profile re-tuning does not break the user-facing surface.

### 2.2 `SlicerProfileBundle` (internal)

The concrete, resolved triple that the slicer worker actually feeds to Orca.

| Field | Type | Notes |
|---|---|---|
| `id` | pk | |
| `intent_preset_ref` | fk | which user-facing preset this realizes |
| `machine_json_ref` | blob/path | full resolved machine settings JSON (post-merge, has top-level `type`) |
| `process_json_ref` | blob/path | full resolved process settings JSON |
| `filament_json_ref` | blob/path | full resolved filament settings JSON |
| `orca_version` | str | e.g. `2.3.2` — part of the estimate-invalidation key |
| `bundle_hash` | str | hash over the three resolved JSONs + orca_version (see §3.3) |
| `source_snapshot_ref` | fk → snapshot | the raw partials + system-profile refs this was resolved from (provenance) |
| `spoolman_overrides_ref` | fk? → override set | optional custom overrides mapped from a Spoolman filament record (§2.4) |
| `created_at` / `superseded_at` | ts | bundles are append-only/versioned, never mutated in place |

**Ownership:** portal owns the *resolved* bundle. The **resolution recipe** (system inheritance + user partials) is owned upstream by Orca's profile tree; the portal snapshots inputs so a resolve is reproducible even if upstream profiles change.

### 2.3 Material classes / generic profiles (MVP set)

Initial generic material classes, each mapping to a default resolved bundle:

- **PLA** — proven (Rosa3D PLA Starter, K1 Max MicroSwiss HF, 0.20 mm).
- **PETG** — generic class, profile TBD from Orca system tree.
- **PCTG** — generic class (present in Spoolman inventory: "PCTG Army Green / Rosa3D").
- **TPU / Rosa Flex** — proven (AI Rosa3D Flex 96A Black + AI 0.20 mm TPU FlowTech, `filament_max_volumetric_speed` 2.8). TPU is the **flagship custom-override case** because flexible filaments need volumetric-speed clamping that generic PLA assumptions get wrong.

**Assumption:** the four classes above are the MVP universe; additional materials (ABS/ASA, nylon, PA-CF, etc.) are post-MVP and arrive as new generic classes + bundles, no schema change.

### 2.4 Spoolman linkage & custom overrides

- A `PrintIntentPreset` (or a per-request line) MAY pin to a **specific Spoolman filament record** when the requester wants a real spool, not just a class. Spoolman is source of truth; the portal links by **profile-style reference** (the B2 insight from the Spoolman discovery: link by profile, not by churning entity id, to isolate from Spoolman entity churn).
- Custom filament + process **overrides** are mapped from the Spoolman `filament.extra` fields (and the inherited `filament.extra.url` purchase link) onto the resolved filament JSON — **especially `filament_max_volumetric_speed`, nozzle/bed temps, and density for TPU and unusual filaments** where the generic class default is wrong.
- The override set is captured in `spoolman_overrides_ref` and folded into `bundle_hash`, so a Spoolman-side change to a mapped field correctly invalidates downstream estimates (§5).

### 2.5 `EstimateRecord`

| Field | Type | Notes |
|---|---|---|
| `id` | pk | |
| `stl_ref` | fk/path + `stl_hash` | which mesh, content-hashed |
| `bundle_ref` | fk → SlicerProfileBundle | which resolved bundle |
| `bundle_hash` | str | denormalized for fast staleness check |
| `orca_version` | str | denormalized |
| `time_seconds` | int | from `; estimated printing time (normal mode)` |
| `filament_g` | float | `; filament used [g]` / `; total filament used [g]` |
| `filament_mm` | float | `; filament used [mm]` |
| `filament_cm3` | float | `; filament used [cm3]` |
| `filament_cost` | float | `; total filament cost` (informational) |
| `settings_ids` | json | `{filament,print,printer}_settings_id` from g-code (attribution) |
| `warnings` | json | classified slicer warnings (e.g. *floating cantilever*) |
| `status` | enum | `fresh` \| `stale` \| `queued` \| `failed` |
| `computed_at` | ts | |

**Estimate key (uniqueness / cache key):** `(stl_hash, bundle_hash)` — and since `bundle_hash` already folds in `orca_version` and Spoolman overrides, that 2-tuple is the complete reproducibility key.

### 2.6 `SourceProfileSnapshot`

Provenance for a resolve: the raw user partials + the system-profile path/refs + the resolver script version used. Lets a bundle be **re-resolved and diffed** if Orca's system profile tree changes upstream. Append-only.

### Ownership topology (one-glance)

```
Spoolman (.190)            Orca system+user profiles            Portal DB
  inventory  ─────────▶    (resolution recipe)  ──────────▶   SourceProfileSnapshot
  filament.extra.url        partials + system tree              │ (provenance)
       │ mapped overrides                                       ▼
       └────────────────────────────────────────────────▶  SlicerProfileBundle (resolved, hashed, versioned)
                                                                │
PrintIntentPreset (portal-owned, user-facing) ──realized by──┘  │
                                                                ▼
                          STL (content-hashed)  ───────▶   EstimateRecord  (key: stl_hash × bundle_hash)
```

---

## 3 — Profile resolver architecture

### 3.1 Why a resolver is needed (proven constraint)

Raw Orca user-profile JSONs are **partial** — they `inherit` from system profiles and lack a top-level `type`. The Orca CLI rejects them directly via `--load-settings` / `--load-filaments`, and `--datadir` does not fix it (verified). So a resolve step is **mandatory**, not optional: merge the system inheritance chain with the user partial, inject `type`, drop the problematic instantiation, emit a full standalone JSON the CLI accepts. The temporary `/home/ezop/tmp/orca_resolve_profiles.py` **proved this path end-to-end** for both PLA and TPU.

### 3.2 Resolver responsibilities (production shape)

1. **Import boundary (read):** read the Orca system profile tree (`.../OrcaSlicer/resources/profiles`) + the user partials. In production these are **vendored/exported artifacts**, not a live read of Fenrir's `/mnt/c/...` — see §7 reproducibility. The export from Fenrir is a one-way snapshot, mirroring the catalog's one-way Windows→.190 rsync discipline.
2. **Inheritance merge:** recursively resolve `inherit` chains (system → user partial), deep-merging keys, user partial wins on conflict.
3. **Normalize:** inject top-level `type` (machine/process/filament), drop the instantiation field that breaks the CLI.
4. **Override layer:** apply Spoolman-mapped custom overrides (§2.4) onto the filament JSON.
5. **Validate:** confirm the merged JSON is CLI-acceptable *before* it becomes a bundle — a dry `--info` / minimal slice smoke check, and a schema assertion that required keys (e.g. `filament_max_volumetric_speed` for TPU) are present and sane.
6. **Hash & version:** compute `bundle_hash`, stamp `orca_version`, write `SlicerProfileBundle` + `SourceProfileSnapshot`.
7. **Export boundary (write):** the resolved triple is the portable artifact; export/import of bundles between environments is by these full JSONs + their hash, never by re-reading Orca state.

### 3.3 Hashing / versioning

- `bundle_hash = H(machine_json ∥ process_json ∥ filament_json ∥ orca_version)` — canonicalized (sorted keys, normalized floats) so cosmetic JSON churn doesn't churn the hash.
- **Why orca_version is inside the hash:** a different Orca build can produce different estimates from identical settings (slicing-engine changes). Folding the version into the hash makes an Orca upgrade a clean invalidation event (§5) rather than a silent estimate drift.
- Bundles are **append-only/versioned** — a re-tune creates a new bundle + hash; old estimates remain attributable to the old hash until recomputed.

### 3.4 Import / export / inheritance — first-class concerns

The task flags these as first-class architecture concerns, and they are: the **inheritance merge** is the load-bearing complexity (it's the reason the naive `--load-settings` path fails), and **import/export** is what makes bundles reproducible across the Fenrir-bench → container-production boundary without a live Fenrir dependency. Both belong in the eventual architecture H2 append as named subsystems, not buried in worker code.

---

## 4 — Slicer-worker architecture

### 4.1 Runtime / container boundary

- **Production:** Orca runs **headless in a containerized slicer-worker** — either a dedicated `slicer-worker` service or an extension of the existing `workers/render/` arq worker pattern (the repo already runs an arq worker for renders; the queue/runtime shape is proven).

  **Open decision (OD-2):** dedicated `slicer-worker` container vs extend `workers/render/`. Leaning dedicated — Orca AppImage + GUI/GL deps (`libgtk-3-0`, `libwebkit2gtk-4.1-0`, etc.) bloat the render image and have a different failure profile (a slice can take minutes; a render is sub-second). PRD/architecture to confirm.
- The container bundles the **Linux OrcaSlicer AppImage v2.3.2** + the verified dep set. AppImage-in-container needs either `--appimage-extract` (run the squashfs contents directly, avoids FUSE in the container) or FUSE; **Assumption:** extract-and-run is the container-friendly path — flag for a spike.
- **No Fenrir, no Windows exe in production.** Fenrir is where profiles are exported from and where feasibility was proven.

### 4.2 Job inputs / outputs

**Input (job payload):** `(stl_ref/stl_hash, bundle_ref/bundle_hash)`. The worker pulls the STL from the cache and the resolved triple JSONs from the bundle store. Nothing else — the 2-tuple is the whole contract.

**Process:** invoke Orca CLI headless with the three resolved JSONs + STL, emit g-code to a temp path.

**Output:** parsed `EstimateRecord` fields (§2.5) from g-code metadata + classified warnings; the g-code itself is **not** retained (large, derivable) beyond the parse — **Open decision (OD-5):** retain g-code for debugging N runs vs parse-and-discard.

### 4.3 STL cache paths

- STLs are content-hashed (`stl_hash`). Cache layout candidate: `<cache_root>/stl/<hash[:2]>/<hash>.stl` (fan-out by hash prefix, same shape the render worker uses for thumbnails).
- Cache is the worker's read source; the API/catalog populates it. **Assumption:** STL source is the existing catalog SoT (`/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` mirrored to `.190`); the slicer worker reads the mirrored copy on `.190`, never Windows directly.

### 4.4 G-code metadata parsing

Parse the **confirmed-present** comment lines (verified in proven slices):

```
; estimated printing time (normal mode)  → time_seconds
; filament used [g] / ; total filament used [g] → filament_g
; filament used [mm]   → filament_mm
; filament used [cm3]  → filament_cm3
; total filament cost  → filament_cost (informational)
; filament_settings_id / ; print_settings_id / ; printer_settings_id → settings_ids (attribution)
```

Parser is a small, **unit-testable** pure function (TDD per AGENTS.md § Execution discipline): g-code text in → typed estimate struct out. Time strings (`3h35m47s`, `8h06m05s`) normalize to seconds. Missing/garbled lines ⇒ classified failure, never a silent zero.

### 4.5 Failure & warning classification

- **Warnings** (slice succeeded, estimate valid): e.g. *floating cantilever* (seen in the PLA proof). Captured in `EstimateRecord.warnings`, surfaced to owner, **non-blocking**.
- **Failures** (no usable estimate): non-manifold mesh, Orca non-zero exit, CLI-rejected profile (should be caught at resolve-time validation §3.2.5, not here), parse failure, timeout. `EstimateRecord.status = failed` + reason; the record exists (so the UI shows "couldn't estimate, here's why") rather than vanishing.
- **Validation pre-check:** Orca `--info` already reports `manifold yes/no` + facet count + volume — run it as a cheap gate before a full slice to fail fast on bad meshes.

### 4.6 Queue / recompute behavior

- Enqueue model: arq job per `(stl_hash, bundle_hash)` that isn't `fresh`. Dedup on the key so two requests for the same part+bundle don't slice twice.
- Concurrency: slices are minutes-long and CPU-heavy — a **small bounded concurrency** (likely 1–2 on `.190`) to avoid starving the API/render workers. **Open decision (OD-6):** concurrency cap + priority (interactive request vs background bulk recompute).
- Recompute is **idempotent** — recomputing a `fresh` record is a no-op (hash already matches).

---

## 5 — Estimate invalidation rules & recompute triggers

An `EstimateRecord` keyed `(stl_hash, bundle_hash)` goes **stale** (→ `queued` → recompute) when any input to that key changes:

| Trigger | Mechanism | Effect |
|---|---|---|
| STL content changes | `stl_hash` changes | new key ⇒ new estimate; old key orphaned (GC later) |
| Resolved bundle re-tuned | new `SlicerProfileBundle` + new `bundle_hash` | estimates on old hash marked `stale`, requeued against new bundle |
| Orca version upgrade | `orca_version` ∈ `bundle_hash` ⇒ hash changes | all estimates effectively stale; bulk recompute |
| Spoolman mapped-override change (e.g. volumetric speed, temp, density) | folded into `bundle_hash` via `spoolman_overrides_ref` | affected bundles re-hash ⇒ dependent estimates stale |
| Spoolman cost-only change (`spool.price`, density unchanged) | **Open decision (OD-7):** cost is derived, not a slice input — recompute the *cost field* arithmetically without re-slicing, OR mark stale | cheap path strongly preferred |

**Design rule:** anything that changes *slicer output* invalidates via the hash. Anything that's pure post-slice arithmetic (cost = mass × price/gram) should be recomputed **without re-slicing** — re-slicing for a price change wastes minutes of CPU. This is the single most important efficiency decision in the recompute design (Pre-Mortem §8 flagged "re-slicing on every Spoolman price tick" as the top self-inflicted-DoS risk).

**Staleness is explicit, never silent:** a stale estimate is *served with a `stale` flag* (UI shows "estimate may be out of date, recomputing") rather than hidden — matching the Spoolman discovery's soft-fail / `stale since HH:MM` pattern.

---

## 6 — MVP vs future / gated capabilities

### MVP (in scope)

- Per-STL estimate for the four generic material classes (PLA, PETG, PCTG, TPU/Rosa Flex).
- Resolver (system+user merge, normalize, validate, hash, snapshot).
- Containerized headless slicer worker, g-code parse, warning/failure classification.
- Estimate cache keyed `(stl_hash, bundle_hash)` with explicit staleness + recompute queue.
- Spoolman-mapped custom filament/process overrides (esp. TPU volumetric speed).
- `PrintIntentPreset` (user-facing) ↔ `SlicerProfileBundle` (internal) separation.
- Reproducible profile export from Fenrir bench → vendored artifacts (no live Fenrir prod dependency).

### Gated / future (explicitly OUT of MVP)

- **Adaptive / variable layer height — GATED.** Proven negative: `adaptive_layer_height=1` did NOT change the layer-Z schedule or estimates vs fixed 0.20 mm for Qstool. It likely needs GUI/project layer-height data or deeper research. Treated as a **future spike**, not an MVP assumption. The data model must not bake in "estimates assume uniform layer height" in a way that blocks a later variable-height bundle — but no MVP work goes here. **Spike exit criterion:** demonstrate that a CLI-only path produces a *different, correct* layer schedule + estimate for a known part.
- Whole-basket / whole-plate slicing & arrangement (non-goal §1).
- Multi-printer optimization / printer auto-selection.
- Additional material classes beyond the four (additive, no schema change).
- Support/mesh-repair tuning UI.
- Retaining g-code / per-layer breakdowns for visualization (OD-5).

---

## 7 — Security / ops considerations

- **No production dependency on Fenrir.** Fenrir `.100` WSL is the research/export bench. Production runs the AppImage in a container. If Fenrir is offline, production estimates are unaffected; only re-export of *new* profiles is blocked.
- **Reproducible profile exports.** Resolved bundles are full JSONs + a hash; profile import/export is by these artifacts, never by re-reading live Orca/Windows state in production. Mirrors the existing one-way Windows→`.190` catalog rsync discipline (portal never writes upstream).
- **Path discipline.** Windows paths (`/mnt/c/Users/ezope/...`) and the Fenrir AppImage path are **bench-only**; they must not appear as production runtime config. Production paths are container-internal cache roots + the `.190` mirrored STL source.
- **Configs/app boundary (HC from Spoolman discovery).** Any docker-network / compose change to reach Spoolman or to add a `slicer-worker` service is a `~/repos/configs` PR, **not** a 3d-portal edit (AGENTS.md § Scope boundaries). The portal initiative owns app-layer worker code; the container topology is configs-side.
- **No secrets in artifacts.** This document contains hostnames/IPs/paths already present in committed docs (acceptable per AGENTS.md § Don't), and **no** tokens, keys, or credentials. Spoolman's `.190` API was observed unauthenticated on localhost; if a network-reachable transport is chosen, the auth env slot from the Spoolman discovery (B4 — "plan the slot even when unused") applies.
- **Resource safety.** Bounded slice concurrency (OD-6) + the "don't re-slice on cost-only changes" rule (§5) prevent the slicer worker from starving the API/render workers or self-inflicting a CPU DoS via recompute storms.

---

## 8 — Pre-Mortem & risk register

Imagining the initiative shipped and failed — why?

| ID | Risk | Mitigation (where addressed) |
|---|---|---|
| R1 | Re-slicing on every Spoolman price tick → recompute storm, CPU starvation | §5 cost-only arithmetic path; OD-7 |
| R2 | Estimates silently drift after an Orca upgrade | `orca_version` ∈ `bundle_hash` (§3.3); upgrade = clean bulk invalidation |
| R3 | AppImage won't run headless in a container (FUSE/GL) | §4.1 extract-and-run spike; dep set already verified on Fenrir |
| R4 | Resolver merge diverges from what Orca GUI would produce → wrong estimates | §3.2.5 validate via real slice smoke; proven for PLA+TPU already |
| R5 | TPU/unusual filament under-clamped volumetric speed → unrealistic time | §2.4 Spoolman override mapping; `filament_max_volumetric_speed` is a required-key assertion |
| R6 | Adaptive layer height assumed to work, ships wrong | §6 GATED with proven negative + spike exit criterion |
| R7 | Live Fenrir dependency sneaks into production via a hardcoded `/mnt/c` path | §7 path discipline; bench-only paths banned from prod config |
| R8 | Whole-basket scope creep (someone "just adds plate slicing") | §1 non-goal #1; per-STL linear-sum is the contract |
| R9 | Estimate cache key incomplete → stale served as fresh | 2-tuple key folds version+overrides; §5 trigger table is exhaustive-by-design |
| R10 | Container topology change made as a 3d-portal edit instead of configs PR | §7 configs/app boundary |

---

## 9 — Open decisions register (for PRD handoff)

- **OD-1** — `quality_tier` enum granularity & its mapping to Orca process layer heights (draft/standard/fine ↔ 0.28/0.20/0.12?). PRD to confirm with real process profiles.
- **OD-2** — Dedicated `slicer-worker` container vs extend `workers/render/`. (Leaning dedicated.)
- **OD-3** — Bundle JSON storage: DB blob vs on-disk artifact + path reference. (Leaning on-disk + ref, matches render thumbnails.)
- **OD-4** — Spoolman transport for override mapping: read-through at resolve time vs periodic mirror. (Inherits the Spoolman-discovery transport OD.)
- **OD-5** — Retain g-code for debugging (N runs) vs parse-and-discard.
- **OD-6** — Slice concurrency cap + priority (interactive vs bulk recompute).
- **OD-7** — Cost-only Spoolman change: arithmetic recompute vs full stale+reslice. (Strongly leaning arithmetic.)
- **OD-8** — STL source for the worker: `.190`-mirrored catalog copy (assumed) vs an explicit upload path for ad-hoc request STLs not in the catalog SoT.
- **OD-9** — Where `PrintIntentPreset` lives module-wise: a new `slicer`/`estimates` module vs folding into the `requests` v2 slot. (Architecture phase call.)
- **OD-10** — AppImage update cadence / pinning policy (2.3.2 pinned; how are upgrades qualified given R2?).

---

## 10 — Action planning & next BMAD step

### Idea 1 — Adopt the per-STL estimate MVP (§6) as the initiative scope

**Why this matters:** smallest slice that delivers owner-visible value (real, reproducible per-part time/filament/cost) on already-proven CLI feasibility, while keeping every hard constraint (no Fenrir prod dependency, no e-commerce, no whole-basket, gated adaptive height) intact and matching single-developer pace.

**Next steps for the BMAD chain:**

1. Operator (or autonomous agent on operator's behalf) invokes **`bmad-correct-course`** with *this artifact* as input context.
2. `bmad-correct-course` routes to the PRD ceremony (`bmad-prd` update intent / initiative-level H2 append to `prd.md` — **not** a new PRD; brownfield).
3. PRD step confirms OD-1, OD-2, OD-7, OD-8, OD-9 explicitly (the load-bearing ones).
4. **Architecture H2 append** (post-PRD, phase-3) adds: the §2 data model, §3 resolver subsystem, §4 slicer-worker subsystem, §5 invalidation rules, and the §7 configs/app boundary note. *This is where the architecture content sketched here graduates into `architecture.md`* — deliberately deferred out of this phase-1 artifact.
5. Epic + story breakdown (likely: resolver, worker/container, parse+cache, invalidation/recompute, Spoolman override mapping — ~5 stories).
6. Sprint planning slots the epic.

**Resources / coordination:** a `slicer-worker` container or render-worker extension (app-side code) + a configs-side PR if a new compose service / network reshape is needed (configs-side, per §7). Profiles exported once from the Fenrir bench into vendored artifacts.

### Idea 2 — Park the gated capabilities (§6) with explicit triggers

Adaptive/variable layer height, whole-basket slicing, multi-printer optimization → listed in the PRD's "deferred-by-design" section with trigger conditions (esp. the adaptive-height spike exit criterion from §6), so a later revisit checks "is the trigger met?" rather than rediscovering the gate.

---

## Session Summary and Insights

### Key achievements

- Problem statement + 8 explicit non-goals locked; per-STL linear-sum contract established as load-bearing.
- Data model sketched with **ownership topology** (Spoolman = inventory SoT, Orca tree = resolution recipe, portal = resolved bundles + estimates), and the user-facing/internal split (`PrintIntentPreset` vs `SlicerProfileBundle`) justified, not just named.
- Resolver and slicer-worker architectures grounded in **proven CLI feasibility** (PLA + TPU slices, g-code metadata lines, the resolver script) rather than speculation.
- Estimate-invalidation trigger table written, with the key efficiency rule (cost-only ⇒ arithmetic, never re-slice).
- Adaptive/variable layer height **explicitly gated** on a proven negative result, with a spike exit criterion.
- 10 open decisions + 10-row risk register ready for direct PRD/architecture handoff.

### Creative breakthroughs and insights

- **Insight 1:** The resolver isn't a convenience — it's *mandatory*, because raw Orca partials are CLI-rejected (proven). This reframes the resolver as a first-class subsystem, not a script.
- **Insight 2:** Folding `orca_version` and Spoolman overrides into `bundle_hash` makes invalidation *fall out for free* — every meaningful change becomes a hash change. The hash is the cache-correctness backbone.
- **Insight 3:** Separating cost (post-slice arithmetic) from slicer-output inputs is the difference between a usable system and a recompute-storm CPU DoS.
- **Insight 4:** Per-STL (not per-basket) is what makes estimates *cacheable and attributable*; whole-plate slicing would destroy both properties.
- **Insight 5:** The Fenrir-bench → vendored-artifact → container-production pipeline mirrors the existing one-way catalog rsync discipline — the repo already has the right mental model for "export from a bench, never depend on it live".

### Session reflections

- Autonomous facilitation suited this topic: the option space is technical and the feasibility spikes already pruned the riskiest unknowns (CLI acceptance, metadata presence, TPU clamping), so the session converges on a single high-confidence MVP rather than needing operator pruning.
- The most under-acknowledged trap is **recompute economics** (R1/OD-7) — easy to build a correct-but-self-DoSing system. The cost-arithmetic carve-out is the antidote.
- **No code was changed.** Exactly one artifact was produced: this file. No PRD, no epic, no story, no sprint-status row.

### Recommended next BMAD step

**`bmad-correct-course`** — invoked with this artifact as input context. Brownfield routing (per AGENTS.md § Workflow expectations): even though the slicer estimate feature is fresh, the codebase is mid-stream brownfield, so vanilla `bmad-prd` *create* is the wrong entry. `bmad-correct-course` will route to the right ceremony (PRD update / initiative-level H2 append, then architecture + epics edits per its recommendation).

### Blocker note (explicit)

**Implementation planning (`t_169b94b9`) remains BLOCKED until this artifact is verified.** This is phase-1 (analysis/discovery) output only. No implementation planning, story breakdown, or sprint-status story creation has been performed, and none should begin until the operator/controller verifies this artifact and the `bmad-correct-course` → PRD → architecture chain has run.

### Closure

This brainstorm/architecture-discovery artifact is complete. No application code was written. No PRD was written. No initiative, epic, story, or sprint-status row was created. The next agent or operator session is expected to invoke `bmad-correct-course` (per the recommendation above) with this file as input context to begin the PRD edit + architecture H2 append cycle.
