---
baseline_commit: 7b081e36f4571b16ec31e621d33e78050e01aacd
---

# Story 32.6: Frontend `PrintIntentPreset` selector + estimate display (fresh / stale / queued / failed / loading / absent) + the narrow estimate read/resolve API seam the UI renders on top of

Status: done

## Story

As a **portal that can resolve a print intent to a content-addressed `SlicerProfileBundle` (Story 32.1), slice it on a containerized worker (32.2), persist a cost-carrying `EstimateRecord` keyed `(stl_hash, bundle_hash)` (32.3), invalidate/recompute one when an input changes (32.4), and map Spoolman `filament.extra` overrides + route price-only vs mapped-override change triggers (32.5) — but whose entire estimate stack is a *backend-only primitive with NO HTTP surface* (the slicer module mounts zero routes; `apps/api/app/router.py` has no estimate router) and NO frontend at all**,
I want **(a) a narrow, read-first estimate API seam — a UI-safe DTO + a read service that resolves a `PrintIntentPreset` to its `bundle_hash` (Story 32.1 `resolve`) and reads the persisted `EstimateRecord` (Story 32.3 `EstimateStore.read`) by content key, plus a guarded optional recompute-enqueue for an already-known stale key (reusing the Story 32.4 primitive) — exposing ONLY what the UI needs and NEVER the resolver/Orca internals; and (b) the frontend `apps/web/src/modules/estimates/` — a `PrintIntentPreset` selector (material class ∈ {PLA, PETG, PCTG, TPU}, quality tier, optional pinned Spoolman spool/overrides) and an estimate display that renders every estimate state honestly: loading (query pending), populated/`fresh`, `stale` ("estimate may be out of date"), `queued` (recompute in flight), soft-fail / `failed` ("couldn't estimate, here's why" + the granular `EstimateFailureReason`), and absent (no record yet) — with finite-number-guarded duration / filament mass+length+volume / informational cost formatting, Spoolman/material override context (incl. the carried `filament.extra.url` purchase link), full i18n parity (`modules.estimates.*` / `modules.slicer.*` in en.json + pl.json), and new visual baselines × the 4 visual projects**,
so that **FR20-PRESET-1 (the `PrintIntentPreset` selector ↔ `SlicerProfileBundle` separation, the preset never leaking Orca internals) and FR20-FAILURE-1's frontend half (warnings non-blocking, failures explicit, soft-fail "Last estimated HH:MM (Xm ago)") are realized, NFR20-I18N-PARITY-1 and NFR20-VISUAL-VERIFICATION-1 are satisfied, and the per-STL estimate MVP (Init 20) has the operator-facing surface it has lacked since Story 32.1 — WITHOUT pulling in the broad catalog↔STL ingestion wiring, the live Spoolman event source, or any checkout/quoting work that is explicitly out of scope**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.1 (FR20-PRESET-1 + FR20-FAILURE-1) + § 4.3 (Epic E32 story sketch — Story 32.6 "frontend `PrintIntentPreset` selector + estimate display + soft-fail/warning/failure states").
Architectural anchor: Decision **AH § override layer / resolver** (the `PrintIntentPreset` IS the resolve input key; the preset carries NO raw Orca keys — `PrintIntentPreset` already "carries no raw layer-height floats / no `filament_max_volumetric_speed`", `models.py:34`) + Decision **AJ § cache / invalidation** (the `EstimateRecord` lifecycle `fresh → stale → queued → fresh` the UI renders; the `(stl_hash, bundle_hash)` content key; the cost-only-arithmetic-vs-mapped-re-slice distinction the UI must reflect honestly). Story 32.1 supplies `resolve` + `compute_bundle_hash`; 32.3 supplies `EstimateStore.read` + `EstimateStatus{fresh,stale,queued,failed}` + `EstimateFailureReason` + `SliceWarning`; 32.4 supplies the recompute-enqueue + the stale/queued transitions; 32.5 supplies the Spoolman-mapped override context (`PrintIntentPreset.spoolman_filament_ref`, the carried `filament.extra.url`) the override-context panel surfaces.
Realizes **FR20-PRESET-1** (preset selector ↔ bundle separation; preset never leaks Orca internals) + **FR20-FAILURE-1 (FE half)** (warnings non-blocking; failures explicit; soft-fail "Last estimated HH:MM (Xm ago)") + **NFR20-I18N-PARITY-1** (`modules.estimates.*` / `modules.slicer.*` keys in BOTH `en.json` + `pl.json`; material names untranslated) + **NFR20-VISUAL-VERIFICATION-1** (new baselines for estimate display + preset selector + soft-fail/warning/failure states × the 4 visual projects, `baseline-reviewed:` sign-off per FR13).
This is **Story 32.6's dev-entry authoring** (per the PRD § Open-decisions note, Stories 32.2–32.6 are authored individually by `bmad-create-story` at their own dev-entry time). Authoring this spec to `ready-for-dev` does NOT itself start `bmad-dev-story` — execution remains controller-routed (ITCM autonomous mode per `[[feedback_itcm_autonomous_mode]]`).
**Codex tag (recommended `gpt-5.5`; controller confirms — route per `[[feedback_codex_model_routing]]`):** dual-adjacency — **public-HTTP-boundary** (a NEW authenticated read endpoint + an optional enqueue endpoint: auth/authorization, input validation of caller-supplied content hashes, no-internal-leak DTO projection) + **data-integrity-as-displayed** (the UI must render `fresh`/`stale`/`queued`/`failed`/`absent` honestly — a stale estimate shown as fresh, or a non-finite cost rendered as a real number, or a price-only recompute mislabeled as a profile change, is a correctness bug the operator acts on). **No subprocess / no Orca** (the FE never slices; the optional enqueue reuses the Story 32.2/32.4 worker primitive and runs on the worker, not in the request).

## Acceptance Criteria

### AC-1 — Narrow estimate read/resolve API seam — UI-safe DTO + read service (the surface the UI renders; NO Orca/resolver internals leak)

The slicer estimate stack has **NO HTTP surface today** — confirmed: `apps/api/app/modules/slicer/` mounts zero routes (no `APIRouter`), and `apps/api/app/router.py` has no estimate router. Per the task scope ("there may be no existing HTTP estimate endpoint yet; if so, 32.6 may include a narrow backend API seam for UI (route/schema/service) but NOT broad slicer architecture"), this story adds the **minimum** seam:

- **New router** `apps/api/app/modules/slicer/router.py` (`APIRouter(prefix="/api/estimates", tags=["estimates"])`), mounted in `apps/api/app/router.py` via `api_router.include_router(estimates_router)` (mirror the `spools_router` wiring pattern, `router.py:15`). The route is **authenticated** (reuse the same auth dependency the other `/api/*` routes use — NOT public; it is NOT added to `apps/api/app/main.py` `_PUBLIC_ROUTES`).
- **New UI-safe DTOs** `apps/web`-facing, in a new `apps/api/app/modules/slicer/schemas.py` (separate from the internal `models.py`, mirroring the `spools/schemas.py` ⟂ `spools/models.py` split — the public DTO is `ConfigDict(extra="forbid")` and exposes ONLY the UI fields). The estimate DTO carries: `status` ∈ {`fresh`,`stale`,`queued`,`failed`,`absent`}, `time_seconds: int | None`, `filament_g/_mm/_cm3: float | None`, `filament_cost: float | None` (informational — AC-4/AC-6), `currency: str | None`, `computed_at: str | None`, a `warnings: list[{code,message}]` projection of `SliceWarning`, a `failure_reason: EstimateFailureReason | None`, and an `override_context` block (AC-5). It MUST NOT carry `settings_ids` (the resolved-profile attribution — internal), `bundle_hash`/`stl_hash` raw layer-height / `filament_max_volumetric_speed` / temps / any g-code / any Orca key, or the raw `SlicerProfileBundle`.
- **New read service** `EstimateReadService` (in `router.py` or a thin `estimate_read.py`): given a `PrintIntentPreset` (built from the request's selector fields — AC-2) **and** an `stl_hash` (a caller-supplied, `validate_content_hash`-gated content hash — see the catalog↔STL gap in AC-9/Dev Notes), it (1) calls `resolver.resolve(intent, …)` to derive the `bundle_hash` (the SAME derivation Story 32.5's dispatch uses — DO NOT re-implement hashing), (2) calls `EstimateStore.read(stl_hash, bundle_hash)`, (3) projects the `EstimateRecord` (or its absence) onto the UI-safe DTO. A miss ⇒ `status="absent"`, all numerics `None` (NOT a 404 — `absent` is a first-class UI state distinct from a transport error, AC-3).
- **Read-only by default:** the read endpoint NEVER enqueues, slices, or writes. It reads the existing cache/store and projects it. (The optional enqueue is AC-1b, separate + guarded.)

**Tests (red→green, backend pytest):** `test_estimate_dto_excludes_settings_ids_and_internals` (the DTO has no `settings_ids`/`bundle_hash`/Orca-key field — `extra="forbid"` + explicit assertion); `test_read_endpoint_resolves_preset_to_bundle_and_reads_record` (fake store returns a `fresh` record ⇒ DTO carries its numerics); `test_read_endpoint_absent_record_returns_status_absent_not_404` (miss ⇒ 200 + `status="absent"`, numerics `None`); `test_read_endpoint_requires_auth` (unauthenticated ⇒ 401, NOT in `_PUBLIC_ROUTES`); `test_read_endpoint_rejects_malformed_stl_hash` (`validate_content_hash` rejects non-hex/short ⇒ 422, no resolve attempted); `test_read_endpoint_projects_failed_record_with_reason` (a `failed` record ⇒ DTO `status="failed"` + `failure_reason` + numerics `None`, never `0`).

### AC-1b — Optional guarded recompute-enqueue seam (re-slice an already-known stale/absent key only — reuses Story 32.4; NOT on-demand slicing of arbitrary new content)

A **separate**, explicitly-guarded endpoint `POST /api/estimates/recompute` (authenticated) that, for an already-resolvable `(stl_hash, preset→bundle_hash)`, calls the **existing** Story 32.4 `recompute.enqueue_recompute` / `invalidate` primitive to (re)queue a slice when the record is `stale`/`absent`. It does **NOT** introduce a new worker, a new job shape, or arbitrary-STL on-demand slicing — it reuses `enqueue.py` / `recompute.py` byte-identically (CALLED, not edited). To bound the R1 self-DoS surface: it is idempotent per the Story 32.4 `_job_id` dedupe, returns `status="queued"`, and does not re-enqueue an already-`queued` key.

- **This sub-AC is OPTIONAL for the MVP slice** — if the controller/dev judges the read seam sufficient for 32.6's display goal, the enqueue endpoint MAY be deferred to a follow-up (recorded in `deferred-work.md`) and the FE renders `absent`/`stale` as terminal-until-the-deferred-event-source-fires (SPOOL-EVT-1, AC-9). If included, it stays within the read seam's narrow contract (no new architecture). The default recommendation: **include the read seam (AC-1) always; include the enqueue seam (AC-1b) only if a button-driven "recompute now" is in the visual scope** — surface the decision in review, don't silently drop it.

**Tests (if included, red→green):** `test_recompute_endpoint_enqueues_via_story_324_primitive` (asserts `enqueue_recompute` called, NOT a new job); `test_recompute_endpoint_idempotent_on_already_queued` (no double-enqueue — the `_job_id` guard); `test_recompute_endpoint_requires_auth`.

### AC-2 — `PrintIntentPreset` selector — material class + quality tier + optional pinned spool/overrides; emits the preset, NEVER an Orca key

New `apps/web/src/modules/estimates/components/PrintIntentPresetSelector.tsx`:

- Selects **material class** ∈ {`PLA`, `PETG`, `PCTG`, `TPU`} (the FR20 set — a named contract, AC-11; material names are **untranslated** per NFR20-I18N-PARITY-1), a **quality tier** (the portal-defined tier set, e.g. draft/standard/fine — sourced from the same constant the backend resolver uses, NOT a UI-local re-spelling), and an **optional pinned Spoolman spool/override** (the Story 32.5 `spoolman_filament_ref` — selected from the existing `useSpoolsSummary()` filament list, displayed by human name, NOT the churning integer id).
- The selector's output is a **`PrintIntentPreset`-shaped** object (material class / quality tier / optional `spoolman_filament_ref`) sent to the AC-1 read endpoint. It MUST NOT expose, accept, or round-trip any raw Orca key (layer height float, `filament_max_volumetric_speed`, nozzle/bed temps) — the preset ↔ bundle separation (FR20-PRESET-1; the `PrintIntentPreset` docstring contract). The bundle resolution happens server-side (AC-1).
- Controlled component with sensible defaults (material class default + standard tier + no pin); changing any field re-keys the estimate query (AC-3). Accessible (AC-7): native/labelled selects, keyboard-navigable, `aria-label`/`<label>` per control.

**Tests (red→green, vitest + RTL):** `test_selector_emits_print_intent_preset_shape` (changing material/tier/pin produces the expected preset object); `test_selector_never_exposes_orca_keys` (no input/option carries `filament_max_volumetric_speed`/layer-height/temp — assert the rendered DOM + emitted payload); `test_selector_material_names_untranslated` (PLA/PETG/PCTG/TPU render verbatim in both locales); `test_selector_pin_uses_filament_ref_not_id` (the pin option value is the stable ref, not `.id`); `test_selector_keyboard_navigable_and_labelled`.

### AC-3 — Estimate display renders every state honestly: loading / fresh / stale / queued / failed / absent

New `apps/web/src/modules/estimates/components/EstimateDisplay.tsx` + a `useEstimate(preset, stlHash)` hook (TanStack Query, mirroring `useSpoolsSummary` — `queryKey: ["estimates", stlHash, presetKey]`, `staleTime` matched to the estimate cache cadence, documented `because`):

- **loading** (query `isPending`) ⇒ a skeleton/spinner state, never a flash of "absent" or "failed".
- **`fresh`** ⇒ the populated estimate (duration / mass / length / volume / informational cost — AC-4), no staleness banner.
- **`stale`** ⇒ the **still-servable** numbers (the `stale` record keeps its values — `estimate_store.py:140` "still SERVABLE") + an explicit "estimate may be out of date" banner. The copy MUST NOT claim it is being recomputed unless the record is actually `queued` (AC-6 honesty).
- **`queued`** ⇒ the prior numbers (if any) + a "recomputing…" indicator (a recompute is genuinely in flight per the Story 32.4 `mark_queued`).
- **`failed`** ⇒ the explicit "couldn't estimate, here's why" surface keyed off `failure_reason` (`parse_failure` / `missing_metadata_line` / `unparseable_time` / `unparseable_numeric` — each i18n'd, AC-7), numerics shown as em-dash NOT `0`.
- **soft-fail** ("Last estimated HH:MM (Xm ago)") ⇒ the FR20-FAILURE-1 copy, computed from `computed_at` via the **existing** `formatTimeOfDay` + `minutesSince` helpers (`apps/web/src/modules/spools/lib/format.ts` — REUSE, do not re-author). Applies to `stale`/`queued` records that still carry numbers.
- **absent** (`status="absent"`, AC-1) ⇒ an explicit "no estimate yet" empty state (distinct from `failed` and from a network error), optionally a "recompute" affordance only if AC-1b is included.
- **network/transport error** (query `isError`) ⇒ a distinct error state (retryable), NEVER conflated with `absent`/`failed`.

**Tests (red→green, vitest + RTL):** one test per state — `test_estimate_display_loading_shows_skeleton`; `test_estimate_display_fresh_shows_values`; `test_estimate_display_stale_shows_servable_numbers_and_out_of_date_banner`; `test_estimate_display_stale_does_not_claim_recomputing` (the AC-6 honesty guard); `test_estimate_display_queued_shows_recomputing`; `test_estimate_display_failed_shows_reason_not_zero`; `test_estimate_display_absent_distinct_from_failed_and_error`; `test_estimate_display_soft_fail_last_estimated_label`; `test_estimate_display_transport_error_is_retryable_not_absent`.

### AC-4 — Duration / filament (mass + length + volume) / informational cost formatting with finite-number guards (no NaN/Infinity/null rendered as a number)

New `apps/web/src/modules/estimates/lib/format.ts` (sibling to the spools `format.ts` — REUSE its `formatWeight`-style em-dash-on-null discipline):

- **Duration** (`time_seconds`) ⇒ a human "Xh Ym" / "Ym" format; `null`/non-finite ⇒ em-dash (`—`), never "0m" or "NaNm".
- **Filament mass** (`filament_g`) ⇒ reuse the spools `formatWeight` convention (g vs kg threshold) OR an estimates-local formatter that shares the contract; **length** (`filament_mm`) ⇒ mm/m; **volume** (`filament_cm3`) ⇒ cm³. Each `null`/non-finite ⇒ em-dash.
- **Cost** (`filament_cost`) ⇒ an **informational** currency string (`currency` from the DTO), labelled as informational (NOT a quote/price — AC-9 out-of-scope checkout/quoting). `null`/non-finite ⇒ em-dash.
- **Finite-number guard (load-bearing):** every formatter MUST treat `NaN`, `Infinity`, `-Infinity`, and `null`/`undefined` identically to a missing value (em-dash) — a non-finite numeric must NEVER render as a digit string. (Backend already gates non-finite at persist via `_reject_non_finite`/`_NUMERIC_FIELDS`; this is the defense-in-depth render-side gate so a transport/serialization edge can't surface a poisoned number.)

**Tests (red→green, vitest):** `test_format_duration_null_and_non_finite_is_em_dash` (parametrized `null`/`NaN`/`Infinity`); `test_format_duration_hours_minutes`; `test_format_mass_length_volume_em_dash_on_null_and_non_finite`; `test_format_cost_informational_with_currency_and_em_dash_on_null`; `test_no_formatter_ever_renders_NaN_or_Infinity`.

### AC-5 — Spoolman / material override context display — WITHOUT leaking Orca internals or raw g-code

The `override_context` DTO block (AC-1) + a `OverrideContextPanel.tsx` surface the material/Spoolman provenance the operator needs, at the right altitude:

- Shows the **material class** + **quality tier** in play, and — when the preset pins a Spoolman filament (32.5 `spoolman_filament_ref`) — the pinned filament's **human display name** + an indicator that **custom Spoolman overrides are applied** (a boolean/badge: "custom filament profile applied"), and the carried **`filament.extra.url` purchase link** (the link 32.5 carries "along for the ride", surfaced as a plain external link — NOT parsed/validated beyond URL-safety; rel="noopener noreferrer").
- It MUST NOT render the **values** of the mapped overrides (no `filament_max_volumetric_speed` number, no nozzle/bed temp, no density float, no layer height) nor any g-code / `settings_ids` / Orca key — only the *fact* that overrides are applied + safe display metadata (name, material class, link). This is the FR20-PRESET-1 "preset never leaks Orca internals" contract enforced at the display layer.
- When no pin / no overrides ⇒ shows the material-class default context (no "custom" badge), honestly.

**Tests (red→green, vitest):** `test_override_panel_shows_material_class_and_pinned_name`; `test_override_panel_shows_custom_applied_badge_when_overrides_present`; `test_override_panel_never_renders_override_values_or_gcode` (assert no vol-speed/temp/density/layer-height/settings_id text in the DOM for a fully-overridden filament); `test_override_panel_purchase_link_is_safe_external` (rel/noopener, no parsing); `test_override_panel_no_pin_shows_default_context_no_badge`.

### AC-6 — Price-only recompute vs mapped-override stale/queued semantics reflected honestly (the 32.5 distinction, surfaced truthfully)

The Story 32.5 load-bearing distinction (cost-only price tick ⇒ arithmetic recompute, **no re-slice**, record stays `fresh` with an updated cost; mapped-override change ⇒ re-hash ⇒ `stale`/`queued` ⇒ re-slice) MUST be reflected truthfully in the UI:

- A record that is `fresh` after a **cost-only** recompute (32.4 `update_cost`, no status change) ⇒ shows as `fresh` with the current cost — the UI MUST NOT label it "out of date" or "recomputing" (it isn't; the cost was arithmetically updated in place).
- A record that is `stale`/`queued` after a **mapped-override** change ⇒ shows the staleness/recomputing copy (AC-3) — because the *profile* changed and a re-slice is the only path to a fresh number.
- The UI MUST NOT **invent** provenance it doesn't have: it renders the record's actual `status` + `computed_at`, not a guess about *why* it is stale. Copy is generic ("estimate may be out of date") unless the DTO actually carries a reason. **No claim of automatic live propagation** — see the SPOOL-EVT-1 caveat (AC-9): because the live Spoolman-change event source + reverse index are deferred, the UI reflects the **server cache/recompute state as it currently is**, and MUST NOT promise "this updates automatically when the Spoolman spool changes" beyond the existing primitives (a stale state appears only when something actually marked it stale).

**Tests (red→green, vitest):** `test_fresh_after_cost_only_recompute_not_labelled_stale` (a `fresh` record with an updated cost ⇒ no out-of-date banner); `test_stale_after_mapped_change_shows_recompute_copy`; `test_ui_does_not_claim_automatic_spoolman_propagation` (no copy/string promises auto-update; the SPOOL-EVT-1 honesty guard — assert the i18n keys carry no "automatically updates" claim).

### AC-7 — Accessibility + i18n + visual-state requirements

- **i18n parity (NFR20-I18N-PARITY-1):** every new user-facing string is a `modules.estimates.*` (and where shared, `modules.slicer.*`) key present in **BOTH** `apps/web/src/locales/en.json` AND `apps/web/src/locales/pl.json` — no hardcoded literal in a `.tsx`. **Material names (PLA/PETG/PCTG/TPU) are NOT translated** (verbatim in both locales). Run the repo's existing i18n-parity check (the locale-key parity test/lint that already guards the other modules) — it must stay green with the new keys present in both files.
- **Accessibility:** every state has an accessible name; `loading` uses `aria-busy`/`role="status"`; `failed`/error states are announced (`role="alert"` or `aria-live`); the selector controls are labelled (AC-2); the purchase link is a real `<a>` with discernible text. The existing `tests/visual/accessibility-axe.spec.ts` axe sweep (or its established pattern) covers the new surface with **zero new violations**.
- **Visual states:** the estimate display + selector render distinctly and legibly across `fresh`/`stale`/`queued`/`failed`/`absent`/`loading` in light + dark (the 4 visual projects, AC-8).

**Tests:** the i18n-parity gate green; an RTL a11y assertion per state (`role`/`aria-*`); axe spec green (AC-8).

### AC-8 — Tests: backend (the API seam), frontend vitest, visual Playwright, no-raw-internals assertion

- **Backend (because the AC-1/AC-1b API seam exists):** the pytest cases enumerated in AC-1/AC-1b — the DTO-projection no-leak test, the resolve→read path, the absent/failed projection, auth + malformed-hash rejection, and (if included) the enqueue-reuses-32.4 test. Full backend `uv run pytest -q` green (baseline + new cases). `ruff format --check` + `ruff check` clean on `apps/api/`.
- **Frontend vitest:** the AC-2/AC-3/AC-4/AC-5/AC-6/AC-7 component + formatter + hook tests above. `npm run -w web test` (vitest) green; lint/typecheck (`tsc`/eslint) clean.
- **Visual Playwright:** new spec(s) under `apps/web/tests/visual/` (e.g. `estimates-display.spec.ts`, `print-intent-preset-selector.spec.ts`) capturing the estimate display in each state (`fresh`/`stale`/`queued`/`failed`/`absent`) + the selector, generating new `__snapshots__` baselines across the **4 visual projects** (`desktop-light`/`desktop-dark`/`mobile-light`/`mobile-dark`, per `tests/visual/playwright.config.ts`). Baselines carry the **`baseline-reviewed:` sign-off per FR13** (NFR20-VISUAL-VERIFICATION-1). Drive the states with mocked API responses (a fixed `computed_at` so the soft-fail label is deterministic — no real clock/slice in the visual test).
- **No-raw-internals assertion (cross-cutting):** an explicit test (backend DTO + frontend DOM) that NO Orca key / `settings_ids` / g-code / raw layer-height / `filament_max_volumetric_speed` / `bundle_hash` ever reaches the response body or the rendered DOM (AC-1/AC-5).

### AC-9 — Scope fence + explicit out-of-scope; the catalog↔STL ingestion gap

- **Backend touches ONLY:** new `apps/api/app/modules/slicer/router.py` + `schemas.py` (+ optional `estimate_read.py`) + one `include_router` line in `apps/api/app/router.py`. The slicer engine modules (`resolver.py`, `recompute.py`, `estimate_store.py`, `enqueue.py`, `worker*.py`, `models.py`, `overrides.py`, `spoolman_invalidation.py`, `gcode_parse.py`, `bundle_store.py`) are **CALLED, not edited** (`git diff main` over them returns zero lines). `EstimateRecord`/`EstimateStatus`/`PrintIntentPreset` shapes unchanged. No Alembic, no new config slot (the resolve + store reads reuse existing wiring), no new Redis key.
- **`main.py` `_PUBLIC_ROUTES` unchanged** — the estimate endpoint is authenticated, NOT public (grep/diff invariant on the `_PUBLIC_ROUTES` tuple).
- **Frontend is additive:** new `apps/web/src/modules/estimates/` (+ the new locale keys + new visual specs/baselines + a mount point on an existing surface). The mount surface for the live catalog-detail embedding is **gated on the catalog↔STL ingestion gap below** — for 32.6, the selector + display are shipped as a self-contained module rendered on a route/surface that supplies an `stl_hash` (or driven by tests with a known hash); wiring catalog parts to their `stl_hash` is NOT this story.
- **The catalog↔STL ingestion gap (surfaced, not silently bridged):** `apps/api/app/modules/catalog/` has **NO `stl_hash` linkage** today (grep confirms zero `stl_hash`/`content_hash` references) — there is no existing path from a catalog part to the content hash the estimate store is keyed by. Building that ingestion (hashing catalog STLs, persisting the part→`stl_hash` map, triggering the first slice) is **broad work that exceeds this story** and is **explicitly OUT OF SCOPE** — recorded as a dependency. 32.6 ships the *display + read seam* keyed by a supplied `stl_hash`; the catalog-side ingestion that feeds real hashes is a separate ingestion story (note in `deferred-work.md`). The story is honest that, until that lands, the live catalog-detail estimate is wired against supplied/known hashes, not auto-derived from every catalog part.

**Out of scope (explicit):**
- **Live Spoolman event source + `filament_ref → estimate-keys` reverse index (SPOOL-EVT-1)** — the deferred 32.5 trigger source; the UI reflects current server cache/recompute state and MUST NOT claim automatic live propagation (AC-6).
- **Inventory writes / any Spoolman mutation** — read-only consumption only (Spoolman = inventory SoT).
- **Checkout / cost quoting / pricing** — `filament_cost` is INFORMATIONAL only; no quote, no cart, no price-to-customer.
- **Raw g-code display / retention** — never rendered, never returned.
- **Adaptive layer height** (and any new slicer profile feature) — not a UI concern here.
- **Deploy automation fix (SW-DEPLOY-1)** — the slicer-worker overlay rebuild gap is noted (Dev Notes), not fixed here.
- **Broad slicer-worker rewrite / new job shape / on-demand arbitrary-STL slicing** — the optional enqueue (AC-1b) reuses the existing 32.4 primitive only.
- **Catalog↔STL ingestion** (above) — separate ingestion story.

**Tests/grep:** `git diff main -- apps/api/app/modules/slicer/resolver.py apps/api/app/modules/slicer/recompute.py apps/api/app/modules/slicer/estimate_store.py apps/api/app/modules/slicer/models.py apps/api/app/modules/slicer/enqueue.py apps/api/app/modules/slicer/worker.py apps/api/app/modules/slicer/overrides.py apps/api/app/modules/slicer/spoolman_invalidation.py` → 0 lines; no new Alembic version file; `apps/api/app/main.py` `_PUBLIC_ROUTES` unchanged; `apps/api/app/core/config.py` Settings field set unchanged.

### AC-10 — NFR20-CONTAINER-1 grep invariant + drift gate stays green

- **Grep invariant:** `grep -rniE "/mnt/c|fenrir|\.exe|[Ww]indows" apps/api/app/modules/slicer/` returns ZERO matches over the new `router.py`/`schemas.py`/`estimate_read.py`. The new frontend module carries no path/exe literal.
- Because 32.6 adds **no** backend config slot, `infra/scripts/check-settings-env-compose.py` must stay at the unchanged alignment (the 32.3/32.4/32.5 50/48/38) — run as a regression guard, not a thing to bump.

**Tests:** extend the slicer no-path-literal grep test to the new files; `check-settings-env-compose.py` → OK (unchanged counts).

### AC-11 — Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

The literals this story introduces are **named contracts**, each pointing to the contract it serves — NOT a peer usage or a default:

| Literal | Location | Contract pointed to |
|---|---|---|
| material-class set `{PLA, PETG, PCTG, TPU}` | `estimates` selector + `modules.estimates.*` | because **"the FR20 supported material-class set (Decision AH resolver inputs); material names are an untranslated portal↔Orca naming convention per NFR20-I18N-PARITY-1, not UI copy"** — sourced from the backend resolver's class set, not re-spelled in the UI |
| quality-tier set | `estimates` selector | because **"the portal-defined quality tier set the resolver maps to Orca process profiles (Decision AH); the UI selects a tier, the server resolves it to a bundle — the tier names are the portal contract, not Orca process-profile names"** |
| `useEstimate` query `staleTime` / `gcTime` | `useEstimate.ts` | because **"the FR20-CACHE-1 estimate freshness cadence — match the estimate cache/recompute cadence so the UI doesn't refetch faster than the server can change state; mirrors the `useSpoolsSummary` 60s/5min Decision-AD pattern"** (point to the cadence contract, NOT copy the spools number blindly — justify the chosen value) |
| em-dash `—` sentinel | `estimates/lib/format.ts` | because **"the no-silent-zero render contract (FR20-FAILURE-1 / EstimateRecord `None`-never-`0`) — a missing/non-finite numeric renders as the absence glyph, never a digit a caller could act on; mirrors the spools `formatWeight` em-dash convention"** |

If a reviewer finds an **arbitrary** timeout / threshold / magic number introduced here, it is a P1 fix-up.

### AC-12 — Determinism gate (NFR20-DETERMINISM-1)

- Backend: three consecutive `uv run pytest tests/test_slicer*.py -q` runs return identical pass counts (the new router/DTO tests are pure — fake store/resolver, no clock in assertions; `computed_at` is fed as a fixed value in tests).
- Frontend: the vitest formatter/component tests are deterministic (the soft-fail `minutesSince` is driven by an injected `now`, mirroring the spools `format.test.ts` pattern — no real `Date.now()` in assertions). The visual specs mock the API + pin `computed_at` so the snapshots are stable across runs.

### AC-13 — Quality gate green (TDD evidence)

`ruff format --check` + `ruff check` clean on `apps/api/`; full backend `uv run pytest -q` green (baseline + new API-seam cases); `npm run -w web test` (vitest) green + `tsc`/eslint clean; the visual Playwright baselines generated + `baseline-reviewed:` signed off across the 4 projects; `git diff --check` clean; the AC-9 diff/grep invariants + AC-10 grep + drift gate green. All assertions are evidence-backed command output in the Dev Agent Record (AGENTS.md § Execution discipline — no "should pass").

## Tasks / Subtasks

> **TDD discipline (AGENTS.md § Execution discipline):** every logic-bearing task writes the failing test FIRST (red), then implements to green, then refactors. Backend: the API seam is asserted with a fake `EstimateStore` + in-process `resolver.resolve` (no real worker/Orca/Redis). Frontend: vitest + RTL with mocked `api`/TanStack Query; the soft-fail label driven by an injected `now`; the visual specs driven by mocked API responses with a pinned `computed_at`. No real slice runs in any test.

- [ ] **T1** (AC-1, AC-1b, AC-8 backend) — Estimate read/resolve API seam + UI-safe DTO *(red→green)*
  - [ ] T1.1 Failing tests: DTO excludes `settings_ids`/internals; resolve→read returns numerics; absent ⇒ `status="absent"` not 404; auth required; malformed `stl_hash` ⇒ 422; failed ⇒ reason + numerics `None` not `0`.
  - [ ] T1.2 Implement `slicer/schemas.py` (UI-safe `extra="forbid"` DTOs), `slicer/router.py` (`/api/estimates` authenticated read; `EstimateReadService` resolving via `resolver.resolve` + `EstimateStore.read`), mount one `include_router` line in `router.py`. `validate_content_hash` the caller hash.
  - [ ] T1.3 (optional, AC-1b — include only if "recompute now" is in visual scope) `POST /api/estimates/recompute` reusing `recompute.enqueue_recompute` byte-identically; idempotent per `_job_id`. If deferred, record in `deferred-work.md`.
- [ ] **T2** (AC-2) — `PrintIntentPresetSelector` *(red→green, vitest+RTL)*
  - [ ] T2.1 Failing tests: emits preset shape; never exposes Orca keys; material names untranslated; pin uses ref not id; keyboard-navigable + labelled.
  - [ ] T2.2 Implement the selector (material class / quality tier / optional Spoolman pin from `useSpoolsSummary`), controlled with defaults, re-keys the estimate query.
- [ ] **T3** (AC-3, AC-6) — `EstimateDisplay` + `useEstimate` hook, all states honest *(red→green)*
  - [ ] T3.1 Failing tests: one per state (loading/fresh/stale/queued/failed/absent/transport-error); stale-not-claiming-recomputing; fresh-after-cost-only-not-stale; no auto-propagation claim.
  - [ ] T3.2 Implement `useEstimate` (TanStack Query, keyed by stlHash+presetKey, documented `staleTime`/`gcTime` `because`) + `EstimateDisplay` rendering each `EstimateStatus` + `absent` + soft-fail label via reused `formatTimeOfDay`/`minutesSince`.
- [ ] **T4** (AC-4) — Finite-guarded formatters *(red→green, vitest)*
  - [ ] T4.1 Failing tests: duration/mass/length/volume/cost em-dash on `null`+`NaN`+`Infinity`; never renders NaN/Infinity; informational cost + currency.
  - [ ] T4.2 Implement `estimates/lib/format.ts` (reuse spools em-dash discipline; finite-number guard on every formatter).
- [ ] **T5** (AC-5) — `OverrideContextPanel` (material/Spoolman context, no internals) *(red→green)*
  - [ ] T5.1 Failing tests: material class + pinned name; custom-applied badge; NEVER renders override values/g-code/settings_ids; safe external purchase link; no-pin default context.
  - [ ] T5.2 Implement the panel from the `override_context` DTO block; `filament.extra.url` as a `rel="noopener noreferrer"` external link.
- [ ] **T6** (AC-7) — a11y + i18n parity *(red→green / gate)*
  - [ ] T6.1 Add all `modules.estimates.*` (+ shared `modules.slicer.*`) keys to BOTH `en.json` + `pl.json` (material names verbatim); run the i18n-parity gate green.
  - [ ] T6.2 a11y roles/aria per state (`role="status"`/`aria-busy` loading, `role="alert"` failed/error, labelled controls); axe spec green.
- [ ] **T7** (AC-8 visual) — Playwright visual baselines × 4 projects *(red→green)*
  - [ ] T7.1 New visual spec(s) driving each state via mocked API + pinned `computed_at`; generate `__snapshots__` across `desktop-light`/`desktop-dark`/`mobile-light`/`mobile-dark`.
  - [ ] T7.2 `baseline-reviewed:` sign-off per FR13 (NFR20-VISUAL-VERIFICATION-1).
- [ ] **T8** (AC-9, AC-10) — Scope fence + grep/drift *(grep/diff)*
  - [ ] T8.1 `git diff main` over the slicer engine modules (resolver/recompute/estimate_store/models/enqueue/worker/overrides/spoolman_invalidation) → 0 lines; `_PUBLIC_ROUTES` unchanged; no Alembic; `config.py` Settings unchanged. Record the catalog↔STL ingestion gap + (if deferred) AC-1b in `deferred-work.md`.
  - [ ] T8.2 NFR20-CONTAINER-1 grep ZERO over the new slicer files; `check-settings-env-compose.py` → OK at the unchanged counts.
- [ ] **T-DET** (AC-12) — Determinism: 3× identical backend pass counts; vitest `now`-injected; visual snapshots stable (mocked API + pinned `computed_at`).
- [ ] **T9** (AC-13, full quality gate) — `ruff format --check` + `ruff check` clean (`apps/api/`); full backend `pytest -q` green; `npm run -w web test` + `tsc`/eslint clean; visual baselines signed off; `git diff --check` clean. Record exact counts in the Dev Agent Record.
- [ ] **T10** (handoff) — dev-story flips `ready-for-dev → review`; code-review owns `→ done`. **Commit / ff-merge / deploy NOT performed by dev-story — controller-owned (ITCM).** Suggested branch `feat/E32.6-frontend-print-intent-preset-estimate-display`; suggested commit scope `feat(web+api): print-intent preset selector + estimate display + narrow estimate read API (Story 32.6, Init 20)`. **Deploy caveat (SW-DEPLOY-1):** the NEW `slicer/router.py`/`schemas.py` are imported by the API; if the optional enqueue (AC-1b) is included, the re-slice still runs on the slicer-worker overlay — any deploy MUST follow the documented overlay rebuild + in-container import smoke (Dev Notes).

## Dev Notes

### Source-of-truth references

- **PRD:** `prd.md` § Initiative 20 — **FR20-PRESET-1** (preset selector ↔ bundle separation; preset never leaks Orca internals), **FR20-FAILURE-1** (warnings non-blocking; failures explicit; soft-fail "Last estimated HH:MM (Xm ago)"), **NFR20-I18N-PARITY-1** (`modules.estimates.*`/`modules.slicer.*` in en+pl; material names untranslated), **NFR20-VISUAL-VERIFICATION-1** (new baselines × 4 projects + `baseline-reviewed:` per FR13), **NFR20-DETERMINISM-1**.
- **Architecture:** `architecture.md` § Initiative 20 — Decision **AH** (the `PrintIntentPreset` resolve input ↔ `SlicerProfileBundle` separation; the preset carries no raw Orca keys) + Decision **AJ** (the `EstimateRecord` `fresh→stale→queued→fresh` lifecycle the UI renders; the cost-only-arithmetic-vs-mapped-re-slice distinction AC-6 surfaces).
- **Epics:** `epics.md` § Initiative 20 § **Story 32.6** — sketch (new `apps/web/src/modules/estimates/`; preset selector material∈{PLA,PETG,PCTG,TPU} + quality tier + optional pinned spool/overrides; estimate display time/mass/length/volume/informational cost + warnings; states loading/populated/stale/soft-fail/failure; preset MUST NOT leak Orca internals; i18n parity; new visual baselines × 4 projects per FR13). **Depends on:** 32.3 + 32.4 (and consumes 32.5 override context).
- **SCP:** `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.1 (FR20-PRESET-1 + FR20-FAILURE-1) + § 4.3 (Story 32.6 sketch).
- **Story 32.1 (done):** `resolver.resolve` / `compute_bundle_hash` (the preset→`bundle_hash` derivation the read service reuses); `PrintIntentPreset` (`models.py:34-52` — carries no raw layer-height/`filament_max_volumetric_speed`; `spoolman_filament_ref` added by 32.5).
- **Story 32.3 (done):** `EstimateStore.read(stl_hash, bundle_hash)` (`estimate_store.py:62`); `EstimateStatus{fresh,stale,queued,failed}` (`models.py:249`); `EstimateFailureReason{parse_failure,missing_metadata_line,unparseable_time,unparseable_numeric}` (`models.py:263`); `EstimateRecord` numeric fields `time_seconds`/`filament_g`/`filament_mm`/`filament_cm3`/`filament_cost` + `settings_ids` (internal, NOT exposed) + `SliceWarning` (`models.py:277-309`); the `None`-never-`0` no-silent-zero contract.
- **Story 32.4 (done):** `recompute.enqueue_recompute` / `invalidate` / `mark_stale` / `mark_queued` / `update_cost` (`estimate_store.py:137+`) — the lifecycle transitions the UI renders; the optional AC-1b enqueue reuses this byte-identically. The cost-only `update_cost` (no status change) vs mapped `mark_stale`/`mark_queued` distinction is AC-6.
- **Story 32.5 (done):** `_bmad-output/implementation-artifacts/32-5-spoolman-mapped-filament-overrides.md` — `PrintIntentPreset.spoolman_filament_ref` (the pin), the carried `filament.extra.url` (purchase link AC-5 surfaces), the cost-only-vs-mapped trigger semantics AC-6 reflects, and the **SPOOL-EVT-1** deferral (no live event source ⇒ the AC-6 no-auto-propagation honesty constraint).
- **Frontend conventions (reuse, do NOT re-author):** `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts` (TanStack Query pattern + `staleTime`/`gcTime` `because`); `apps/web/src/modules/spools/lib/format.ts` (`formatWeight`/`formatTimeOfDay`/`minutesSince` + em-dash-on-null + injected-`now` test discipline); `apps/web/src/lib/api.ts` (`api<T>` client); `apps/web/src/locales/{en,pl}.json` (i18n keys); `apps/web/tests/visual/playwright.config.ts` (the 4 projects + `snapshotPathTemplate`); `apps/web/tests/visual/accessibility-axe.spec.ts` (axe pattern).
- **Backend API conventions (reuse):** `apps/api/app/modules/spools/router.py` (`APIRouter(prefix=…)` + auth dependency pattern) + `apps/api/app/modules/spools/schemas.py` (the public-DTO ⟂ internal-model split, `extra="forbid"`); `apps/api/app/router.py` `include_router` wiring; `apps/api/app/main.py` `_PUBLIC_ROUTES` (the estimate route is NOT added here — authenticated).
- **Memory entries (read before implementation):** `[[feedback_scp_pre_enumeration_phase]]` (§ A pre-enum, § B coherence/cache-topology, § C magic-constant pointing — AC-11); `[[feedback_codex_model_routing]]` (32.6 review-tier: dual-adjacency public-HTTP-boundary + data-integrity-as-displayed; recommended `gpt-5.5`); `[[feedback_itcm_autonomous_mode]]` (dev-story execution controller-routed; spec authoring does not start dev-story).

### Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

Run 2026-06-02 against post-Story-32.5 repo state (`main` @ `7b081e3`):

1. **Reality confirmed by focused grep/read (the load-bearing facts):**
   - **No HTTP estimate endpoint exists.** `apps/api/app/modules/slicer/` mounts ZERO routes (no `APIRouter`); `apps/api/app/router.py` includes no estimate router. ⇒ AC-1 adds the narrow seam (route/schema/service), per the task scope.
   - **No catalog↔STL linkage.** `grep` over `apps/api/app/modules/catalog/` finds ZERO `stl_hash`/`content_hash` references — there is no path from a catalog part to the content hash the estimate store is keyed by. ⇒ catalog ingestion is OUT OF SCOPE (AC-9); 32.6 reads by a supplied `stl_hash`.
   - `EstimateStore.read(stl_hash, bundle_hash)` + `iter_*` exist (`estimate_store.py:62/195/214`); `EstimateStatus` has exactly `{fresh, stale, queued, failed}` — `absent`/`loading` are FE/transport states the DTO/query add (AC-3).
   - Frontend modules today: `admin`, `auth`, `catalog`, `landing`, `spools` — NO `estimates` module yet (NEW). The spools module supplies the TanStack-Query + formatter + visual-spec patterns to mirror.
   - The 4 visual projects are `desktop-light`/`desktop-dark`/`mobile-light`/`mobile-dark` (`tests/visual/playwright.config.ts:18`).
2. **NEW (Story 32.6 owns):** backend `apps/api/app/modules/slicer/router.py` + `schemas.py` (+ optional `estimate_read.py`); frontend `apps/web/src/modules/estimates/` (`components/PrintIntentPresetSelector.tsx`, `components/EstimateDisplay.tsx`, `components/OverrideContextPanel.tsx`, `hooks/useEstimate.ts`, `lib/format.ts` + tests); new locale keys in `en.json` + `pl.json`; new `apps/web/tests/visual/estimates-*.spec.ts` + `__snapshots__`; new `apps/api/tests/test_estimate_api.py` (or extend a slicer test file).
3. **MODIFIED (minimal/additive):** `apps/api/app/router.py` (one `include_router` line); `apps/web/src/locales/{en,pl}.json` (new keys); a mount point on an existing FE surface for the estimates module.
4. **Contracts UNTOUCHED:** the slicer engine (`resolver.py`, `recompute.py`, `estimate_store.py`, `enqueue.py`, `worker*.py`, `models.py`, `overrides.py`, `spoolman_invalidation.py`, `gcode_parse.py`, `bundle_store.py`) — CALLED not edited (AC-9 diff invariant). `apps/api/app/main.py` `_PUBLIC_ROUTES` (estimate route authenticated, not public). `apps/api/app/core/config.py` Settings (no new slot). `apps/api/app/modules/spools/*` (consumed read-only for the filament pin list). No Alembic. No new Redis key. `~/repos/configs/*` (HC2 — no configs-side gate for the spec; SW-DEPLOY-1 deploy caveat below).

**Net scope:** 2 new backend files (router + schemas, + optional read service) + 1 `include_router` line + 1 new frontend module (selector + display + override panel + hook + formatters + tests) + 2 locale-file appends + new visual specs/baselines × 4 projects + 0 engine edits + 0 Alembic + 0 new config slot + 0 catalog-ingestion work + 0 Spoolman write + 0 checkout/quoting.

### Cache-coherence / boundary enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

FE cache-topology table (the React Query / TanStack surfaces this story owns + the boundaries it must respect):

| Concern | Source: Story 32.6 (this story) | Related surface |
|---|---|---|
| Estimate query cache | `useEstimate` `queryKey: ["estimates", stlHash, presetKey]` — re-keyed on any selector change (AC-2/AC-3); `staleTime`/`gcTime` matched to the FR20-CACHE-1 estimate cadence (AC-11) | Mirrors `useSpoolsSummary` (`["spools","summary"]`, 60s/5min Decision AD). A selector change MUST produce a new key (a new bundle ⇒ a different estimate) — a stale key would show a *different* preset's estimate. |
| Filament pin list | reuses `useSpoolsSummary()` (read-only) for the optional Spoolman pin options (AC-2) — NO second spools fetch, NO new spools query key | Cache-coherent with `/spools/summary` by construction (same key). The pin is by stable `spoolman_filament_ref`, not `.id` (32.5 / Init 19 B2). |
| Status honesty (fresh/stale/queued/failed/absent) | the display renders the record's ACTUAL `status` + `computed_at` (AC-3/AC-6); `absent` = `status="absent"` (a 200 miss, AC-1), distinct from `failed` and from a transport error | The single most important display-correctness chokepoint: a stale shown as fresh, or absent conflated with failed/error, misleads the operator. The 5 states + loading + transport-error are mutually exclusive branches. |
| Cost-only vs mapped provenance | a `fresh`-after-`update_cost` record shows NO staleness; a `stale`/`queued`-after-mapped record shows the recompute copy (AC-6) | The 32.5 R1 distinction surfaced truthfully: the UI never invents "why" beyond the DTO's `status`/`reason`; never claims auto-propagation (SPOOL-EVT-1 deferred). |
| No-internal-leak DTO projection | the `slicer/schemas.py` DTO (`extra="forbid"`) projects ONLY UI fields; `settings_ids`/`bundle_hash`/Orca keys/g-code excluded server-side (AC-1) + the panel never renders override values (AC-5) | FR20-PRESET-1 enforced at BOTH the API boundary and the render layer (defense in depth) — a leak at either is a contract breach. |
| Finite-number render guard | every formatter treats `NaN`/`Infinity`/`null` as em-dash (AC-4) | Defense-in-depth over the backend `_reject_non_finite` persist gate — a transport/serialization edge can't surface a poisoned digit string. |
| Public-HTTP boundary | the read endpoint is authenticated (NOT in `_PUBLIC_ROUTES`), `validate_content_hash`-gates the caller `stl_hash`, and resolves server-side (the FE never derives a bundle) (AC-1) | New attack surface: auth, input validation, no-leak projection. The optional enqueue (AC-1b) reuses the 32.4 `_job_id` dedupe to bound the R1 self-DoS. |

Decision rule: the **status-honesty chokepoint** (AC-3/AC-6) + the **no-internal-leak projection** (AC-1/AC-5) are the load-bearing coherence concerns — the UI renders the record's true state at the right altitude (no Orca internals), and the API never returns more than the UI-safe DTO.

### Magic-constant contract pointing (per `[[feedback_scp_pre_enumeration_phase]]` § C)

The four named contracts (the material-class set, the quality-tier set, the `useEstimate` cache cadence, the em-dash sentinel) each point to the contract they serve in the AC-11 table — none points to a peer usage or a framework default. **If the dev reaches for an arbitrary timeout / threshold / poll interval, STOP** — the estimate query cadence is the only timing constant, and it points to the FR20-CACHE-1 freshness budget (justified, not copied blindly from the spools 60s).

### Threat-vector enumeration

Story 32.6 routes to the higher review tier for **dual-adjacency: public-HTTP-boundary + data-integrity-as-displayed**. Survey:

- **Public-HTTP boundary (NEW surface — the real new risk):**
  - **Auth/authorization.** The estimate read + optional enqueue endpoints are **authenticated** (reuse the standard `/api/*` auth dependency); NOT added to `_PUBLIC_ROUTES`. Asserted (`test_read_endpoint_requires_auth`). An unauthenticated estimate read would expose owner-side informational cost + Spoolman context.
  - **Input validation.** The caller-supplied `stl_hash` is `validate_content_hash`-gated (64-hex, AC-1) BEFORE any resolve/store read — no path/injection vector, no resolve on garbage. The preset fields are constrained to the material-class/tier enums (no free-form Orca key accepted — AC-2).
  - **No-internal-leak projection.** The DTO (`extra="forbid"`) returns ONLY UI fields; `settings_ids`/`bundle_hash`/Orca keys/g-code excluded (AC-1) + the panel never renders override values (AC-5). A leak would breach FR20-PRESET-1 + expose resolver internals.
  - **R1 self-DoS (optional enqueue).** The AC-1b enqueue reuses the 32.4 `_job_id` dedupe + does not re-enqueue an already-`queued` key — a button-mash can't fan out a re-slice storm. (If AC-1b is deferred, this surface is absent.)
- **Data-integrity-as-displayed (the correctness risk the operator acts on):**
  - **Stale-shown-as-fresh / status conflation.** Mitigated by the AC-3/AC-6 honest per-state rendering + the `absent`≠`failed`≠`error` distinction + `test_estimate_display_stale_does_not_claim_recomputing` / `test_fresh_after_cost_only_recompute_not_labelled_stale`.
  - **Non-finite rendered as a number.** Mitigated by the AC-4 finite-number guard on every formatter (`NaN`/`Infinity`/`null` ⇒ em-dash) + the backend `None`-never-`0` contract — defense in depth.
  - **False auto-propagation claim.** Mitigated by the AC-6 SPOOL-EVT-1 honesty constraint (no copy promises automatic live Spoolman update; the UI reflects current server state only).
- **No PII; no g-code ever rendered/returned; no Spoolman write; no checkout/quote (informational cost only).**

### Runtime / deploy verification (SW-DEPLOY-1 — note, NOT in-scope to fix)

The NEW `apps/api/app/modules/slicer/router.py` + `schemas.py` are imported by the API process (the new estimate route). If the **optional AC-1b enqueue** is included, the re-slice it enqueues still runs on the `slicer-worker` overlay (`portal-slicer-worker`, layered on `portal-api`), which imports the slicer modules. Per **SW-DEPLOY-1** (`_bmad-output/implementation-artifacts/deferred-work.md`), `infra/scripts/deploy.sh` rebuilds/restarts only the base stack — NOT the configs-side `slicer-worker` overlay — so a deploy can leave the worker on stale slicer modules.

**Therefore, whenever this story is committed/merged/deployed (controller-owned, ITCM):** the API/web deploy follows the standard path; **if AC-1b is included**, the deploy MUST also follow the documented manual overlay rebuild + in-container import smoke (so the worker can resolve/slice with the new modules). If AC-1b is deferred (read-only seam), no worker code path changes and the standard API/web deploy suffices — but the new `slicer/router.py`/`schemas.py` import must be smoke-checked on the API container.

```bash
# standard API + web deploy (read-only seam) — verify the new estimate route imports + serves:
#   curl -fsS (authenticated) /api/estimates?... → UI-safe DTO, no internals
# IF AC-1b enqueue included, ALSO rebuild the worker overlay (SW-DEPLOY-1):
docker compose --env-file .env \
  -f docker-compose.yml \
  -f /mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.yml \
  --profile slicer-worker up -d slicer-worker
# then verify from inside 3d-portal-slicer-worker-1: slicer modules import + Orca runnable.
```

### Out of scope (explicit)

- **Catalog↔STL ingestion** — hashing catalog STLs, persisting the part→`stl_hash` map, triggering the first slice. No such linkage exists today (grep-confirmed); building it is a separate ingestion story (`deferred-work.md`). 32.6 reads by a supplied `stl_hash`.
- **Live Spoolman event source + reverse index (SPOOL-EVT-1)** — deferred from 32.5; the UI reflects current server cache/recompute state, MUST NOT claim automatic live propagation (AC-6).
- **Inventory writes / Spoolman mutation** — read-only (Spoolman = inventory SoT).
- **Checkout / cost quoting / pricing** — `filament_cost` is INFORMATIONAL only.
- **Raw g-code display / retention** — never rendered, never returned.
- **Adaptive layer height** + any new slicer profile feature.
- **Deploy automation fix (SW-DEPLOY-1)** — noted, not fixed.
- **Broad slicer-worker rewrite / new job shape / on-demand arbitrary-STL slicing** — the optional AC-1b enqueue reuses the existing 32.4 primitive only.

### Gate plan

| Gate | Command | Pass condition |
|---|---|---|
| Backend API-seam TDD | `uv run pytest tests/test_estimate_api.py -q` (from `apps/api/`) | all green (DTO no-leak + resolve→read + absent/failed projection + auth + malformed-hash + optional enqueue) |
| Full backend | `uv run pytest -q` (from `apps/api/`) | baseline (post-32.5 count) + new cases, 0 failures |
| Frontend unit | `npm run -w web test` (vitest) | all green (selector + display states + formatters + override panel + hook) |
| Frontend types/lint | `tsc --noEmit` + eslint on `apps/web/` | clean |
| Visual baselines | Playwright `tests/visual/estimates-*.spec.ts` × 4 projects | baselines generated + `baseline-reviewed:` signed off (NFR20-VISUAL-VERIFICATION-1) |
| i18n parity | the repo locale-key parity gate | `modules.estimates.*`/`modules.slicer.*` present in en+pl; material names verbatim |
| a11y | `tests/visual/accessibility-axe.spec.ts` (or its pattern) | zero new violations |
| Determinism (AC-12) | 3× `pytest tests/test_slicer*.py -q` + vitest | identical pass counts; `now`-injected; snapshots stable |
| Scope diff (AC-9) | `git diff main -- apps/api/app/modules/slicer/{resolver,recompute,estimate_store,models,enqueue,worker,overrides,spoolman_invalidation}.py apps/api/app/main.py` | 0 lines (engine + `_PUBLIC_ROUTES` untouched) |
| Container grep (AC-10) | `grep -rniE "/mnt/c\|fenrir\|\.exe\|[Ww]indows" apps/api/app/modules/slicer/` | 0 matches |
| Drift gate (AC-10) | `infra/scripts/check-settings-env-compose.py` | OK (unchanged counts) |
| Whitespace | `git diff --check` | clean |
| Runtime (SW-DEPLOY-1) | new-route import smoke (+ overlay rebuild IF AC-1b) | controller-owned post-deploy; NOT a dev-story gate |

### Risks

- **R-32.6-1 (status mislabel, HIGH):** a stale/queued estimate shown as fresh, or absent conflated with failed/error, misleads the operator about a number they act on. Mitigation: the AC-3/AC-6 per-state honest rendering + the explicit no-claim-recomputing / no-auto-propagation tests; the 5 states + loading + transport-error are mutually exclusive branches.
- **R-32.6-2 (internals leak, HIGH):** an Orca key / `settings_ids` / g-code / raw override value reaching the response body or the DOM breaches FR20-PRESET-1. Mitigation: the `extra="forbid"` DTO server-side projection (AC-1) + the panel never-render-values test (AC-5) — defense in depth at both boundaries.
- **R-32.6-3 (non-finite render, MEDIUM):** a `NaN`/`Infinity` reaching a formatter renders a poisoned digit string. Mitigation: the AC-4 finite-number guard on every formatter + the backend `None`-never-`0` persist contract.
- **R-32.6-4 (unauthenticated/over-broad endpoint, MEDIUM):** a public or unvalidated estimate endpoint exposes owner cost/Spoolman context or accepts garbage hashes. Mitigation: authenticated (not in `_PUBLIC_ROUTES`) + `validate_content_hash` gate + enum-constrained preset (AC-1/AC-2); optional enqueue reuses the 32.4 `_job_id` dedupe.
- **R-32.6-5 (catalog↔STL gap misread as in-scope, MEDIUM):** mistaking 32.6 for the story that wires every catalog part to a live estimate would balloon scope into the missing ingestion. Mitigation: explicitly surfaced as OUT OF SCOPE (AC-9 + Dev Notes + `deferred-work.md`); 32.6 ships the display + read seam keyed by a supplied `stl_hash`.
- **R-32.6-6 (visual baseline flake, LOW):** a real-clock `computed_at` would make the soft-fail label + snapshots non-deterministic. Mitigation: mocked API + pinned `computed_at` + injected `now` (AC-12).

### Dev Agent Record

#### Context Reference

- Story spec: this file. Baseline `main` @ `7b081e3`; suggested feature branch `feat/E32.6-frontend-print-intent-preset-estimate-display`.

#### Agent Model Used

- `bmad-dev-story` (controller-routed ITCM autonomous mode) on `claude-opus-4-8[1m]`. Implementation across a partial dev-story pass + a focused continuation pass (the focused pass hit `max_turns`); this entry is the controller-verified close-out of the now-green gates. AC-1b (recompute-enqueue endpoint) DEFERRED per the sprint decision (read-only seam sufficient for the display MVP, no "recompute now" button in visual scope) — recorded in `deferred-work.md`.

#### Debug Log References

- Focused continuation pass hit `max_turns`; gates re-verified by the controller after the run (evidence below). One controller-side type-only fix-up applied (see Completion Notes) — no app-logic change.

#### Completion Notes List

- **AC-1b deferred (honest):** the optional recompute-enqueue endpoint (`POST /api/estimates/recompute`) was NOT implemented — the read-only seam (AC-1) is sufficient for the 32.6 display MVP, no "recompute now" affordance is in visual scope, and deferring avoids the SW-DEPLOY-1 slicer-worker overlay-rebuild entanglement (read-only seam ⇒ standard API/web deploy). Recorded in `deferred-work.md`. The `EstimateDisplay` renders `absent`/`stale` as terminal-until-the-deferred-event-source-fires (SPOOL-EVT-1), as the AC-1b text permits.
- **Controller-side type-only test-helper fix (honest disclosure):** `apps/web/tests/visual/estimates-display.spec.ts` had its `stubEstimate` route-helper return type changed to `Promise<unknown>` because Playwright `page.route()` returns `Promise<Disposable>` in this repo's version — a type-only change to make `npm run typecheck` green. No runtime/app-logic behavior changed; it touches a visual-test helper signature only.
- **Backend targeted (green):** `cd apps/api && uv run pytest tests/test_estimate_api.py tests/test_route_enforcement_gate.py tests/test_spools_routes.py -q` → `28 passed, 67 warnings in 3.57s`.
- **Backend ruff (clean):** `uv run ruff format --check app/modules/slicer/router.py app/modules/slicer/schemas.py app/modules/slicer/estimate_read.py tests/test_estimate_api.py` → `4 files already formatted`; `ruff check` over the same paths → `All checks passed!`.
- **Web unit (green):** `cd apps/web && npm test -- --run src/modules/estimates` → `6 passed (6)` test files, `64 passed (64)` tests.
- **Web typecheck (green):** `npm run typecheck` → green (after the type-only test-helper fix above).
- **Web lint (green):** `npm run lint` → green (only the pre-existing React-version warning line, no new findings).
- **Visual (green):** new 32.6 baselines generated via `npm run test:visual -- tests/visual/estimates-display.spec.ts tests/visual/print-intent-preset-selector.spec.ts --update-snapshots`, then the normal focused visual rerun → `24 passed (9.4s)`. 24 new snapshot files under `apps/web/tests/visual/__snapshots__/estimates-display.spec.ts/` + `.../print-intent-preset-selector.spec.ts/` (× the 4 visual projects). `baseline-reviewed:` sign-off is pending independent review.
- **Whitespace:** `git diff --check` → clean.
- **Status:** `review` (independent review pending; code-review owns `→ done`). Commit/ff-merge/deploy NOT performed — controller-owned (ITCM).

#### Review Fix-ups (independent adversarial review → REQUEST_CHANGES → addressed, 2026-06-02)

An independent adversarial review returned **REQUEST_CHANGES** with two blockers; both are now fixed (scope kept narrow — no commit/deploy; Status stays `review`).

- **Blocker 1 (read path mutated the real bundle store) — FIXED.** `GET /api/estimates` is documented + intended read-only ("never enqueues, slices, or writes"), but the production resolver path could write bundle/snapshot files: `SettingsEstimateResolver.resolve_preset` called Story 32.1 `resolve(…, store=BundleStore(…), …)`, and `resolve` persists a fresh bundle + provenance snapshot (`store.write_snapshot` / `store.write_bundle`) on a content MISS. Fix: a `_ReadOnlyBundleStore(BundleStore)` adapter in `estimate_read.py` (a NEW 32.6 file — the engine `bundle_store.py` is UNtouched, AC-9 preserved) whose `write_bundle` / `write_snapshot` are no-ops returning the would-be path; `resolve_preset` now resolves through it. A content HIT is still served from disk and the `bundle_hash` derivation is byte-identical; a miss just computes the hash in-memory without persisting. The real (writing) `BundleStore` continues to back every OTHER caller (Story 32.5 dispatch, the worker, `resolve_intent`) — the adapter is local to the read seam. **Regression test (production resolver path, NOT the fake):** `test_production_resolver_read_path_does_not_mutate_bundle_store` (`tests/test_estimate_api.py`) points settings at the checked-in vendored fixtures + a tmp bundle-store root, runs the real `SettingsEstimateResolver.resolve_preset`, and asserts ZERO `*.json` written under the store root — with a guard that the SAME resolve against a real writing store DOES persist (so the no-write assertion is not vacuous). Verified the test catches the regression: reverting the adapter to `BundleStore` makes it fail (2 stray files: a bundle + a snapshot); restored ⇒ green.
- **Blocker 2 (AC-1b deferral not recorded in `deferred-work.md`) — FIXED.** The Completion Notes claimed AC-1b was "Recorded in `deferred-work.md`", but no Story 32.6 entry existed. Appended a `## Deferred from: Story 32.6 dev-story (2026-06-02)` section with **EST-RECOMPUTE-1** (the optional guarded `POST /api/estimates/recompute` enqueue endpoint — why deferred, fix sketch, SW-DEPLOY-1 deploy note) and **EST-INGEST-1** (the catalog↔STL ingestion gap, AC-9). Existing deferred-work entries left intact.

**Fix evidence (re-run after the changes):**
- Backend targeted: `cd apps/api && uv run pytest tests/test_estimate_api.py tests/test_route_enforcement_gate.py tests/test_spools_routes.py -q` → `29 passed, 67 warnings` (was 28; +1 = the new production-path regression test).
- `tests/test_estimate_api.py` alone → `11 passed` (was 10; +1).
- Backend ruff on changed files: `uv run ruff format --check app/modules/slicer/estimate_read.py tests/test_estimate_api.py` → `2 files already formatted`; `ruff check` over the same → `All checks passed!`.
- Frontend untouched by these fixes ⇒ the heavy FE gates were NOT re-run (they remain at the v0.2 evidence above).

#### Independent Re-review → APPROVE + Controller Close-out (2026-06-02)

After the two blockers were fixed, the controller re-ran the full gate set and an independent adversarial re-review was performed on the fixed diff. Verdict: **APPROVE**. Story closed `review → done` (controller-owned ITCM close-out; NO commit/ff-merge/deploy/branch-delete performed here).

- **Independent re-review verdict: APPROVE.** The re-review specifically confirmed:
  - **Blocker 1 fixed** — `estimate_read.py:197-223` + `246-269` (the `_ReadOnlyBundleStore` no-write adapter makes the production `GET /api/estimates` read path non-mutating while computing the byte-identical `bundle_hash`); the route carries no write/enqueue/slice path.
  - **Regression test quality good** — `tests/test_estimate_api.py:380-431` (`test_production_resolver_read_path_does_not_mutate_bundle_store`) exercises the real `SettingsEstimateResolver.resolve_preset` and is non-vacuous (the same resolve against a real writing store DOES persist).
  - **Blocker 2 fixed** — the Story 32.6 deferral section exists in `deferred-work.md` (≈ lines 159-192: EST-RECOMPUTE-1 AC-1b enqueue + EST-INGEST-1 catalog↔STL ingestion); existing deferred entries intact.

- **Controller gates after the fix (all green):**
  - Backend target: `cd apps/api && uv run pytest tests/test_estimate_api.py tests/test_route_enforcement_gate.py tests/test_spools_routes.py -q` → `29 passed, 67 warnings in 3.36s`.
  - Backend ruff: `ruff format --check` → `4 files already formatted`; `ruff check` → `All checks passed!`.
  - Web units: `6 passed` (test files) / `64 passed` (tests).
  - Web typecheck: green.
  - Web lint: green (only the pre-existing React-version warning line).
  - Focused visual: `24 passed (9.4s)` — the 32.6 baselines (× 4 projects) `baseline-reviewed:` signed off at close-out (NFR20-VISUAL-VERIFICATION-1, FR13).
  - `git diff --check`: clean.
  - YAML sprint status: `review` → `done` at this close-out.

- **Close-out actions:** Status `review → done`; sprint-status row `32-6-frontend-print-intent-preset-estimate-display` → `done`; deferred-work entries (EST-RECOMPUTE-1 / EST-INGEST-1) kept intact. Commit / ff-merge / deploy / branch-delete remain controller-owned (ITCM) and were NOT performed by this close-out. epic-32 stays `in-progress`; epic-32-retrospective stays `pending`.

#### File List

**Backend (new):**
- `apps/api/app/modules/slicer/router.py` — `/api/estimates` authenticated read router
- `apps/api/app/modules/slicer/schemas.py` — UI-safe `extra="forbid"` DTOs
- `apps/api/app/modules/slicer/estimate_read.py` — `EstimateReadService` (resolve→read→project); **review fix:** adds the `_ReadOnlyBundleStore` no-write adapter so the production read path never mutates real bundle-store artifacts (Blocker 1)
- `apps/api/tests/test_estimate_api.py` — backend API-seam tests; **review fix:** adds `test_production_resolver_read_path_does_not_mutate_bundle_store` (production-resolver no-write regression, Blocker 1)

**Backend (modified):**
- `apps/api/app/router.py` — one `include_router` line mounting the estimates router

**Docs (modified):**
- `_bmad-output/implementation-artifacts/deferred-work.md` — **review fix:** Story 32.6 deferral section (EST-RECOMPUTE-1 AC-1b enqueue + EST-INGEST-1 catalog↔STL ingestion), Blocker 2

**Frontend (new):**
- `apps/web/src/modules/estimates/components/PrintIntentPresetSelector.tsx` (+ `.test.tsx`)
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx` (+ `.test.tsx`)
- `apps/web/src/modules/estimates/components/OverrideContextPanel.tsx` (+ `.test.tsx`)
- `apps/web/src/modules/estimates/components/EstimatesPanel.tsx` — module mount surface
- `apps/web/src/modules/estimates/hooks/useEstimate.ts` — TanStack Query hook
- `apps/web/src/modules/estimates/lib/format.ts` (+ `.test.ts`) — finite-guarded formatters
- `apps/web/src/modules/estimates/lib/preset.ts` (+ `.test.ts`) — preset shape/key helpers
- `apps/web/src/modules/estimates/lib/i18n-honesty.test.ts` — SPOOL-EVT-1 no-auto-propagation copy guard
- `apps/web/src/routes/estimates/index.tsx` — self-contained route surface (supplies `stl_hash`)
- `apps/web/tests/visual/estimates-display.spec.ts` — visual spec (+ `__snapshots__/`)
- `apps/web/tests/visual/print-intent-preset-selector.spec.ts` — visual spec (+ `__snapshots__/`)

**Frontend (modified):**
- `apps/web/src/lib/api-types.ts` — estimate DTO types
- `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` — `modules.estimates.*` / `modules.slicer.*` keys (material names verbatim)
- `apps/web/src/routeTree.gen.ts` — auto-regenerated for the new route

### Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-06-02 | v0.1 | Story spec authored to `ready-for-dev` (`bmad-create-story`; spec-only, no code). Baseline `main` @ `7b081e3`. Confirmed by focused grep/read: NO HTTP estimate endpoint exists (slicer module mounts zero routes) ⇒ AC-1 narrow read/resolve API seam; NO catalog↔STL linkage ⇒ ingestion OUT OF SCOPE. SPOOL-EVT-1 (live Spoolman event source/reverse index) stays deferred ⇒ AC-6 no-auto-propagation honesty constraint. | bmad-create-story |
| 2026-06-02 | v0.2 | `in-progress → review`. `bmad-dev-story` implemented the read-only seam (AC-1) + the `apps/web/src/modules/estimates/` module (selector + display + override panel + hook + finite-guarded formatters + preset helpers) + i18n keys (en+pl) + visual baselines × 4 projects. **AC-1b DEFERRED** (read-only seam sufficient; no "recompute now" in visual scope) → `deferred-work.md`. Gates (controller-verified after a focused continuation pass hit `max_turns`): backend targeted `28 passed`; ruff format+check clean on the new files; web unit `6 files / 64 tests passed`; typecheck + lint green; focused visual `24 passed` with 24 new baselines (sign-off pending review); `git diff --check` clean. One **controller-side type-only** fix to `tests/visual/estimates-display.spec.ts` (`stubEstimate` → `Promise<unknown>` to match Playwright `page.route()` `Promise<Disposable>`; no app-logic change). Independent review pending; code-review owns `→ done`. Commit/merge/deploy NOT performed (controller-owned ITCM). | bmad-dev-story |
| 2026-06-02 | v0.3 | **Independent adversarial review → REQUEST_CHANGES → 2 blockers fixed** (Status stays `review`; narrow scope; no commit/deploy). **Blocker 1:** the production read path (`SettingsEstimateResolver.resolve_preset` → Story 32.1 `resolve`) could write bundle/snapshot files on a content miss; fixed with a `_ReadOnlyBundleStore` no-write adapter in `estimate_read.py` (engine `bundle_store.py` untouched, AC-9 preserved) + a production-resolver-path regression test (`test_production_resolver_read_path_does_not_mutate_bundle_store`, proven to catch the regression). **Blocker 2:** appended the missing Story 32.6 deferral to `deferred-work.md` (EST-RECOMPUTE-1 AC-1b enqueue + EST-INGEST-1 catalog↔STL ingestion). Re-run gates: backend targeted `29 passed` (+1); `tests/test_estimate_api.py` `11 passed` (+1); ruff format+check clean on the changed backend files. Frontend untouched ⇒ heavy FE gates not re-run. | bmad-dev-story (review fix-up) |
| 2026-06-02 | v0.4 | **`review → done`** (controller-owned ITCM close-out). Independent adversarial **re-review of the fixed diff → APPROVE** (confirmed Blocker 1 fixed at `estimate_read.py:197-223`/`246-269` + route has no write/enqueue/slice path; regression test quality good at `test_estimate_api.py:380-431`; Blocker 2 fixed in `deferred-work.md` ≈ lines 159-192). Controller gates green: backend target `29 passed, 67 warnings in 3.36s`; ruff `4 files already formatted` / `All checks passed!`; web units `6 passed / 64 passed`; typecheck green; lint green (only the pre-existing React-version warning); focused visual `24 passed (9.4s)` with `baseline-reviewed:` sign-off; `git diff --check` clean. Deferred-work entries (EST-RECOMPUTE-1 / EST-INGEST-1) kept intact. Commit / ff-merge / deploy / branch-delete NOT performed (controller-owned ITCM); epic-32 stays `in-progress`, epic-32-retrospective stays `pending`. | bmad-code-review (close-out) |
