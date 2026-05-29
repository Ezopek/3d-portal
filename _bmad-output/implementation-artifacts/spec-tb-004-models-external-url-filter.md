---
title: 'TB-004 GET /api/models external_url filter for dedup'
type: 'feature'
created: '2026-05-11'
status: 'done'
route: 'one-shot'
---

# TB-004 GET /api/models external_url filter for dedup

## Intent

**Problem:** Agent-runbook pre-flight check #4 (dedup-by-source-URL before creating a model) has no good primitive today. `Model.source` is an enum, not a URL; the URL lives on a `ModelExternalLink(model_id, source, url)` join row. The public-read SoT router exposes NO endpoint that filters models by external_link URL. Agent workarounds: text-search via `GET /api/models?q=<keywords>` (fragile — searches `name_en`/`name_pl`/`slug`, not link URLs) or POST external_link and catch `409 source_conflict` (half-state risk if model-create succeeded but external-link failed for a different reason).

**Approach:** Add `external_url=<url>` query parameter to `GET /api/models` that filters via subquery on `ModelExternalLink.url`. Returns 0 or 1 row typically. Agent uses for idempotent re-import: hit → return existing UUID; miss → proceed with create. Implementation is a one-line `where` clause in `list_models`, mirroring the existing `tag_ids` AND-subquery pattern — outer SELECT shape unchanged, so paging/sort/eager-loading pipelines all apply seamlessly. OpenAPI surface auto-enriches via Story 4.3's hookup (verified — `external_url` shows up in `/api/openapi.json`).

## Files

- [`apps/api/app/modules/sot/service.py`](../../apps/api/app/modules/sot/service.py) — `list_models` signature extended with `external_url: str | None = None`; subquery filter added (`Model.id.in_(...)`).
- [`apps/api/app/modules/sot/router.py`](../../apps/api/app/modules/sot/router.py) — pass-through query param + description update.
- [`apps/api/tests/test_sot_models_list.py`](../../apps/api/tests/test_sot_models_list.py) — 4 new pytest cases: exact match returns owner; no-match returns empty (with control row on a different URL — catches silent-ignore); soft-deleted owner excluded by default + surfaced via `include_deleted=true`; AND-combines with `status` (with a control model on a different URL — catches silent-ignore under combined filters).
- [`docs/agents-add-model-runbook.md`](../../docs/agents-add-model-runbook.md) — Principles "Idempotence" + Pre-flight check #4 rewritten to use the new primitive with a `curl --data-urlencode` example. **Intro paragraph (Story 4.1 fingerprint baseline `49280ada…`) untouched** — verified post-edit.

## Suggested Review Order

1. [Diff — service.py subquery](../../apps/api/app/modules/sot/service.py) — the surgical `where` clause; mirror `tag_ids` AND pattern.
2. [Diff — router.py signature](../../apps/api/app/modules/sot/router.py) — pass-through + description.
3. [Diff — test file](../../apps/api/tests/test_sot_models_list.py) — 4 tests including the control-row hardening.
4. [Diff — runbook update](../../docs/agents-add-model-runbook.md) — fingerprint-preserving edits to non-intro sections.
5. [Triage backlog](../triage-backlog.md) — TB-004 row closed with commit reference + TB-008 candidate added (index on `ModelExternalLink.url` — pre-existing scale-question, deferred from review P2 #3).

## Adversarial review summary

`feature-dev:code-reviewer` (no conversation context) returned 0×P0 + 2×P1 + 2×P2 + 1×P3. Patches applied in same working tree:

- **P1 #1** (90) — tests used f-string interpolation `f"/api/models?external_url={target_url}"` instead of `params=` dict; latent URL-encoding trap for any future test URL with `?`/`&`/`#`. Converted all 4 test HTTP calls to `client.get(url, params={...})`.
- **P1 #2** (85) — tests used raw `"other"` string for `ModelExternalLink.source` instead of the typed `ExternalSource.other` enum. Coupling gap if the enum ever drifts. Imported `ExternalSource` and used the member.
- **P2 #4** (80) — `test_list_models_external_url_no_match_returns_empty` had no seeded control model — passed vacuously if filter were entirely broken. Strengthened with a control `ModelExternalLink` row on a DIFFERENT URL that proves the filter is actually consulted.

Deferred:
- **P2 #3** (82) — `ModelExternalLink.url` has no index → subquery is a full table scan. Acceptable at homelab scale (low-thousands of rows) but should be filed for before any large-scale import batch. **Promoted to TB-008 candidate in triage-backlog.**
- **P3 #5** — commit scope nit; using `feat(sot):` per reviewer's recommendation (new SoT functionality, not a bugfix).

## Verification

- `.venv/bin/pytest -q`: 407 passed (4 new + 403 existing).
- `.venv/bin/ruff check` + `--format check` on changed files: clean.
- OpenAPI: `external_url` present in `/api/openapi.json` `paths./api/models.get.parameters`; description mentions it; Story 4.3's `test_openapi_agent_surface.py` 25 tests still pass.
- Runbook fingerprint after edit: `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` (matches `infra/.runbook-fingerprint` — first non-empty line after H1 untouched).
