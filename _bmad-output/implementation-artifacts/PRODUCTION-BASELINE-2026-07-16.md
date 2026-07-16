# Production Baseline — 2026-07-16

**Purpose:** Draw a clean line under all prior BMAD-driven work so the tag-taxonomy /
model-catalog rebuild starts from a zero-debt board. `main` as of this date is
accepted as **production**. Everything before this point is frozen; nothing
open is carried forward implicitly.

## What this freeze declares

- **`main` is production.** All 39 epics tracked in `sprint-status.yaml` are `done`;
  all 186 stories are `done`; every retrospective is `done` or `optional`. There
  are **zero** open (`in-progress` / `review` / `backlog`) items.
- **BMAD engine is clean.** Installed surface is `6.10.0` (`_bmad/_config/manifest.yaml`).
  Our `_bmad/custom/` overrides are **empty templates only** (comments, no real
  overrides) — there is no customization debt to shed.
- **The next initiative starts fresh.** The tag-taxonomy / model-catalog rebuild
  begins from `docs/design/HANDOFF-tagi-fasetowe.md`, planned with current BMAD,
  not by resuming any item below.

## Cancelled residual work (not shipping under the old system)

Both are commented out in `sprint-status.yaml` (matching the existing
`# 38-1 … superseded` convention) rather than marked `done`, to keep the record honest:

| Item | Was | Why cancelled |
|------|-----|---------------|
| `38-4-member-offer-request-estimate-cta` | epic-38, `backlog` | Superseded by the offer/catalog surface being reworked in the rebuild. |
| `4-6-add-model-from-url-cli` | epic-4, `backlog` | "Add model from URL" is absorbed into the model-catalog rebuild. |

`epic-38` was closed (`in-progress → done`) since its only remaining story was cancelled.

## Deferred-work ledger — archived

`deferred-work.md` → `archive/deferred-work-closed-2026-07-16.md` (frozen banner added).
Its still-open entries are **known, non-blocking debt**, explicitly not carried forward:

- `DSG-1..5` — `deploy.sh` robustness (errno swallowing, non-atomic state write, TOCTOU, etc.)
- `TB-015-D1` — touch/mobile pointer-events inside `backdrop-blur` ancestor
- `SPOOL-PREQ-1-D1` — blank-field Spoolman filaments → degenerate `spoolman_filament_ref`
- `PROFILE-LIB-GUARD-1` — block deleting profile blocks referenced by offers
- `PROFILE-OFFER-SYNC-1` — detect stale published offers after profile-block upsert

If any resurfaces as a real problem, re-triage it as a fresh item under the new
initiative — do not reopen the archived ledger as a live backlog.

## Housekeeping applied to `sprint-status.yaml`

- Collapsed duplicate status breadcrumbs (`epic-11/21/22/23/24` each appeared twice
  during status transitions) to a single `done` entry.
- Added the missing epic keys `epic-25` and `epic-29` for previously orphaned
  stories `25-1` and `29-1`.
- Retrospectives `epic-11..17` corrected from the invalid `backlog` status to `optional`.
- Refreshed the header banner; `last_updated: 2026-07-16`.
