---
title: 'Story 22.2 — FE carousel gallery-tier consumption (share + catalog detail, TB-037 FE)'
type: 'feature'
status: 'ready-for-dev'
story_id: '22.2'
epic: 'E22 — Image Tier Pipeline + Symmetric Fullscreen Viewer'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-037 FE'
fr_ref: 'FR16-CAROUSEL-TIER-1'
architectural_anchor: 'Decision W (consumer side)'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.4-mini per [[feedback_codex_model_routing]] routine FE)'
estimated_effort: '30-45 min FE URL-construction changes + visual baseline regen + vitest no-regression'
created: '2026-05-24'
---

# Story 22.2 — FE carousel gallery-tier consumption (TB-037 FE)

Status: ready-for-dev

## Story

As share recipients (anonymous /share/$token) AND authenticated catalog detail browsers (/catalog/$modelId),
I want the in-page carousel main frame to load `?variant=gallery` (~150-500 KB) instead of the full original (4-8 MB) blob,
so that initial paint is dramatically faster + the existing share-anon nginx caps (Story 19.2 limit_rate + limit_conn) no longer fire on legitimate carousel use (closes TB-037 FE consumption — Story 22.1 backend pipeline is shipped).

## Acceptance Criteria

1. **AC1 — ShareCarousel main frame consumes `?variant=gallery`** in `apps/web/src/routes/share/$token.tsx`. Currently the main frame loads URLs from `data.images` (which the backend emits as `/api/share/{token}/files/{fid}/content` — no variant). Change to append `?variant=gallery` to the main-frame URL. Thumb strip URLs stay unchanged (already serving `?variant=thumb` via separate construction). Story 22.1 round-2 commit `05ad8f0` enabled the share asset endpoint to serve the `.gallery.webp` sibling for this query param.

2. **AC2 — CardCarousel main frame consumes `?variant=gallery`** in `apps/web/src/ui/custom/CardCarousel.tsx`. The catalog detail page's main carousel frame (currently loads full-res original via `/api/models/{id}/files/{fid}/content`) appends `?variant=gallery`. Card grid (`ModelCard.tsx`) stays `?variant=thumb` (Story 20.1 baseline preserved).

3. **AC3 — Visual baselines regen.** Per NFR16-VISUAL-VERIFICATION-1: regenerate Playwright visual baselines for:
   - `/share/$token` route across 4 viewport projects (desktop-1920, desktop-1024, mobile-iphone-12, mobile-pixel-5 — verify against existing project config).
   - `/catalog/$modelId` detail route across the same 4 viewports.
   The visual diff should be near-zero (perceptually identical) since gallery tier renders at a size larger than typical viewport scaling — the perceptual quality stays high. Operator visual sign-off via baseline-reviewed commit-msg trailer per [[feedback_frontend_visual_verification]].

4. **AC4 — Vitest no-regression.** Existing carousel tests (`ShareCarousel` / `CardCarousel`) continue to PASS at their current count. If any test pattern-matches on the exact URL shape (e.g. `expect(url).toBe('/api/share/X/files/Y/content')`), update the expectation to include `?variant=gallery` for main-frame URLs.

5. **AC5 — npm run build CLEAN with no code-split warnings.** Per [[feedback_pre_merge_gate_checklist]] mandatory gate.

6. **AC6 — Codex review CLEAN (gpt-5.4-mini routine FE).** Per [[feedback_codex_model_routing]].

## Tasks / Subtasks

- [ ] **T1 — ShareCarousel URL extension** (AC: #1)
  - [ ] T1.1 — Locate `apps/web/src/routes/share/$token.tsx:ShareCarousel` (~lines 145-260). Identify main-frame URL construction site.
  - [ ] T1.2 — Append `?variant=gallery` to main-frame URLs. Thumb strip URLs already use `?variant=thumb` — verify they're constructed separately (not from the same source).

- [ ] **T2 — CardCarousel URL extension** (AC: #2)
  - [ ] T2.1 — Locate `apps/web/src/ui/custom/CardCarousel.tsx` main-frame URL construction.
  - [ ] T2.2 — Append `?variant=gallery` to main-frame URLs. Card-grid (ModelCard.tsx) NOT touched — stays `?variant=thumb` per Story 20.1.

- [ ] **T3 — Tests** (AC: #4)
  - [ ] T3.1 — Run vitest on ShareCarousel + CardCarousel test files; update URL expectations if any pattern-match on exact URL shape.
  - [ ] T3.2 — Full vitest run no-regression.

- [ ] **T4 — Visual baselines** (AC: #3)
  - [ ] T4.1 — Run `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts --update-snapshots` for `/share/*` + `/catalog/*` specs.
  - [ ] T4.2 — Operator visual sign-off via baseline-reviewed trailer in commit message OR separate visual review (orchestrator handles trailer).
  - [ ] T4.3 — Verify hook-context PASS matches standalone (per Init 9 NFR9-DETERMINISM-1 spirit).

- [ ] **T5 — Pre-merge gates** (AC: #5)
  - [ ] T5.1 — `cd apps/web && npm run typecheck` exit 0.
  - [ ] T5.2 — `cd apps/web && npm run lint` exit 0.
  - [ ] T5.3 — `cd apps/web && npx vitest run` PASS.
  - [ ] T5.4 — `cd apps/web && npm run build` exit 0, no chunk-split warnings.

- [ ] **T6 — Commit + Codex + deploy** (orchestrator)
  - [ ] T6.1 — `feat(share,catalog): carousel main-frame consumes gallery variant (Story 22.2, TB-037 FE)`.
  - [ ] T6.2 — Codex review gpt-5.4-mini.
  - [ ] T6.3 — Auto-deploy to .190.
  - [ ] T6.4 — Operator hands-on verify post-deploy on .190 for both surfaces.

## Dev Notes

### Backend handshake (already shipped)

- Story 22.1 (commit a04a61f) — backend gallery tier worker + variant routing on authenticated `/api/models/{id}/files/{fid}/content?variant=gallery`.
- Story 22.1 round-2 (commit 05ad8f0) — variant routing extended to anonymous `/api/share/{token}/files/{fid}/content?variant=gallery`.
- Both endpoints fall back silently to the original blob when the `.gallery.webp` sibling is missing — backward-compatible during the gallery-tier-rollout window before the backfill runs on .190.

### URL construction expectations

**ShareCarousel** likely builds URLs from `data.images` directly. The simplest pattern: append `?variant=gallery` at the consumption site, e.g. `<img src={`${url}?variant=gallery`} />`. Verify the existing thumb-strip construction (likely separate URL builder that already includes `?variant=thumb`).

**CardCarousel** receives image URLs as props (probably from a parent that constructs them from ModelFile rows). Find the construction site OR the consumption site — extension can land at either layer. Match existing pattern in the file.

### What NOT to touch

- `ModelCard.tsx` card-grid — stays `?variant=thumb` per Story 20.1 baseline.
- `Viewer3DInline` STL preview surface — uses its own URL construction via srcOverride (Story 20.3); not affected.
- `AnonymousImage` blob-cache logic in ShareCarousel — the cache key includes the full URL so different variants produce different cache buckets (correct behavior; no change needed).

## File List

**MODIFIED (2):**
- `apps/web/src/routes/share/$token.tsx` — ShareCarousel main-frame URL extension
- `apps/web/src/ui/custom/CardCarousel.tsx` — main-frame URL extension

**Visual baseline regen expected:** ~8-16 PNGs (2 routes × 4 viewports × 1-2 baseline modes).

**Diff stats expected:** ~5-15 LOC code changes + visual baseline regen.

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Typecheck | `cd apps/web && npm run typecheck` | Exit 0 |
| Lint | `cd apps/web && npm run lint` | Exit 0 |
| Vitest | `cd apps/web && npx vitest run` | All PASS, count preserved or grown |
| Build | `cd apps/web && npm run build` | Exit 0, no warnings on /share or /catalog chunks |
| Visual baselines | `npx playwright test --update-snapshots` | New baselines generated; hook-context PASS matches standalone |
| Codex review | `codex review --commit <SHA> -c review_model="gpt-5.4-mini"` | CLEAN or fix-up cycle |

## References

- [Init 16 SCP §4.1 Story 22.2](sprint-change-proposal-2026-05-24-init16.md#41-epic-e22--image-tier-pipeline--symmetric-fullscreen-viewer)
- [architecture.md § Decision W consumer side](../planning-artifacts/architecture.md#decision-w--gallery-tier-variant-pipeline-shape-epic-22--fr16-tier-1)
- [prd.md § FR16-CAROUSEL-TIER-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep)
- Backend shipped: Story 22.1 commits a04a61f + 05ad8f0
- Memory: [[feedback_codex_model_routing]] (gpt-5.4-mini routine FE), [[feedback_frontend_visual_verification]], [[feedback_pre_merge_gate_checklist]]

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
