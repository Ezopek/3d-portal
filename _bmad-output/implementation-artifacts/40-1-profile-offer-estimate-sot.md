# Story 40.1 — Offer-driven estimate backfill (Profile Offer = SoT)

- **Epic:** 40 — Profile Offers as estimate Source of Truth
- **Status:** dev-ready
- **Branch:** `feat/E40.1-offer-estimate-backfill`
- **Date:** 2026-06-19
- **Parent correct-course:** `_bmad-output/planning-artifacts/profile-offers-estimate-sot-correct-course-2026-06-19.md`
- **Scope:** backend + pytest only. No FE, no DB, no Alembic, no infra. No live mutation.
  **40.1 implements** replacing the existing post-publish material-default hook with an
  offer-driven hook (not a follow-up).

## Cel

Recompute estymat napędzany **ofertą**, nie macierzą `material_defaults`. Każda opublikowana
oferta ma `published_bundle_hash` z własnego łańcucha; backfill kolejkuje estymaty dla
`(każdy katalogowy STL × published_bundle_hash oferty)`. To wprost naprawia bieżący ból:
`material_defaults_count=0 → cells_total=0` mimo widocznych/domyślnych/opublikowanych ofert.

## Kontekst (kod, zweryfikowany)

- `profile_offer.py` — sidecar oferty niesie `published_bundle_hash`, `publish_state`,
  `validation_state`, `visibility`, `is_default`; `list_offers(root)`, `read_offer(root, id)`.
- `profile_publish.publish_offer` — rozwiązuje łańcuch (`resolve_chain`, `profile_selection=None`)
  i zapisuje `published_bundle_hash` na sidecar (już poprawne; **bez zmian**).
- `matrix_backfill.py` — `enqueue_matrix_for_all_stls(resolved_cells, …)` robi freshness
  pre-check (`estimate_store.read(stl_hash, bundle_hash)` + `status==fresh`) i idempotentne
  kolejkowanie; zwraca liczniki `enqueued/already_fresh/missing_stl/errors`. **Reużywamy.**
- `estimate_store` — klucz `(stl_hash, bundle_hash)`; `read` nigdy nie rzuca na miss.
- `admin_router.py` — `POST /api/admin/policy/default-matrix-backfill` + `DefaultMatrixBackfillResponse`
  jako wzór kształtu odpowiedzi i auth gate.

## Acceptance Criteria

1. **Czysta enumeracja ofertowa.** Nowa funkcja w `matrix_backfill.py`:
   `enumerate_offer_cells(offers: list[dict], *, visible_only: bool, offer_id: str | None = None) -> list[ResolvedMatrixCell]`
   - jedna komórka na ofertę z `publish_state=="published"` **i** niepustym `published_bundle_hash`
     **i** `validation_state != "invalid"`;
   - `visible_only=True` → tylko `visibility=="visible"`;
   - `offer_id` ustawione → tylko ta oferta;
   - `bundle_hash = sidecar["published_bundle_hash"]` (BEZ `resolve_chain`, hash już zapisany);
   - **nie** czyta `material_defaults` ani `policy`.
   - czysta funkcja, bez I/O poza przekazanymi `offers`.
2. **Nowy endpoint.** `POST /api/admin/profiles/offers/recompute-estimates` (admin auth jak inne
   `admin_router` trasy):
   - body: `{ "dry_run": bool = true, "visible_only": bool = true, "offer_id": str | null = null, "max_cells": int | null = null }`;
   - waliduje `offer_id` przez `is_valid_offer_id` gdy podany:
     - malformed/non-hex → 422 `invalid_offer_id`;
     - well-formed but missing → 404 `offer_not_found`;
   - jeśli `offer_id` istnieje, ale oferta nie kwalifikuje się (unpublished / brak
     `published_bundle_hash` / invalid / hidden przy `visible_only=true`), zwraca 422 z
     `reason_category` zamiast cichego pustego sukcesu;
   - `dry_run=true` → liczy `cells_total` i `would_enqueue` bez kolejkowania;
   - `dry_run=false` → woła `enqueue_matrix_for_all_stls` i zwraca realne `enqueued`;
   - `inspected` w odpowiedzi oznacza liczbę katalogowych STL rozważonych przez helper; jeśli
     `max_cells` ustawione i `cells_total × inspected > max_cells`, endpoint zwraca 422 przed
     enqueue.
3. **Kształt odpowiedzi** identyczny jak `DefaultMatrixBackfillResponse`
   (`dry_run, inspected, cells_total, cells_resolved, cells_resolve_failed, would_enqueue,
   enqueued, already_fresh, missing_stl, errors`). `cells_resolve_failed` zawsze 0 (hash gotowy).
4. **Naprawa bólu (dowód):** przy N opublikowanych widocznych ofertach z `published_bundle_hash`,
   M katalogowych STL i **zero** `material_defaults`: dry-run zwraca `cells_total == N` i
   `would_enqueue == N*M - already_fresh`. (Stary `default-matrix-backfill` w tych warunkach
   nadal zwraca `cells_total=0` — to oczekiwane; nie zmieniamy jego endpointu w 40.1.)
5. **Idempotencja:** ponowny realny recompute bez zmian w STL/ofertach → `enqueued==0`,
   wszystko `already_fresh`.
6. **Post-publish hook bez material-default dependency.** Obecny hook po `publish_offer`
   (`admin_router.py` around `slicer.offer_publish_matrix_hook`) używa `enumerate_matrix_cells` +
   `ProfilePolicyStore`. **40.1 zastępuje go** offer-driven enumeracją dla tej jednej oferty,
   bez czytania `material_defaults`; failure jest logowany i nadal nie rollbackuje publikacji.
7. **Brak regresji:** sam `publish_offer` (publikacja bundle), member
   `GET /api/estimates?offer_id=…`, oraz istniejący `default-matrix-backfill` endpoint pozostają
   bez zmian zachowania (testy zielone).
8. **Bezpieczeństwo:** brak logowania refów Orca/sekretów w czysto; logi tylko agregaty
   (offer_id + liczniki), spójne ze strukturą `slicer.matrix_backfill.*`.

## Tasks

- [ ] `enumerate_offer_cells` w `matrix_backfill.py` (+ ewentualnie `MatrixCell.material` → "" lub
      osobny lekki typ; preferowane: zwracać `ResolvedMatrixCell` z `bundle_hash` i minimalnym
      `cell`, by `enqueue_matrix_for_all_stls` działał bez zmian).
- [ ] `OfferRecomputeRequest` / `OfferRecomputeResponse` (lub reużycie `DefaultMatrixBackfillResponse`).
- [ ] Endpoint `POST /api/admin/profiles/offers/recompute-estimates` w `admin_router.py`
      (auth + walidacja `offer_id` + dry-run gałąź + opcjonalny `max_cells`).
- [ ] Zastąpić post-publish material-default hook w `publish_profile_offer` offer-driven hookiem
      dla `offer_id`.
- [ ] Pytest: enumeracja (visible_only, offer_id, pomijanie invalid/unpublished/bez-hasha),
      dowód AC-4 (`cells_total=N`, zero material_defaults), idempotencja AC-5, dry-run vs real.
- [ ] Structured-log assert (agregaty, brak wycieku refów).

## Tests (pytest, `apps/api`)

- `test_enumerate_offer_cells_*` — published+visible+valid+hash ⇒ komórka; pomija
  unpublished / invalid / hidden(`visible_only`) / brak `published_bundle_hash`.
- `test_offer_recompute_dry_run_counts_without_material_defaults` — AC-4 (rdzeń poprawki).
- `test_offer_recompute_real_enqueues_then_idempotent` — AC-5.
- `test_offer_recompute_offer_id_scope` + walidacja złego `offer_id` oraz niekwalifikowalnej
  oferty (unpublished/brak hasha/invalid/hidden przy `visible_only`).
- `test_offer_recompute_max_cells_rejects_before_enqueue` — zarówno globalnie, jak i przy
  `offer_id` scope.
- `test_publish_offer_hook_uses_offer_bundle_without_material_defaults` — asercja, że hook używa
  nowej enumeracji/`published_bundle_hash`, a nie starego `ProfilePolicyStore`/`material_defaults`.
- `test_offer_recompute_does_not_touch_policy_matrix` — stary endpoint niezmieniony.

## Out of scope (kolejne stories)

- FE relabel/przepięcie przycisku + ProfilePolicyPanel→Advanced → **40.2**.
- Member-list filtr `visible` + wybór `is_default` w FilesTab → **40.3**.
- Demote/usunięcie legacy grid + `material_defaults` z produktu → **40.4** (gated).

## Gates (AGENTS.md)

- `ruff format --check` + `ruff check` (apps/api) · `pytest` (apps/api) zielone.
- External review (routine: Aider / `laura-aider-review-diff` per agent rulebook).
- `infra/scripts/check-all.sh` zielone przed ff-merge do `main`.
- Brak zmian UI ⇒ `test:visual` nie wymagane dla tej story.
- Deploy po zielonym wg workflow (commit `feat(api):` wyzwala deploy).

## Safety

- Recompute domyślnie **dry-run**; realne kolejkowanie tylko `dry_run=false`.
- Append-only store; klucz `(stl_hash, bundle_hash)` niezmienny; brak migracji/usuwania.
- Brak mutacji systemów live z poziomu planu/story; backfill ograniczony freshness pre-checkiem.
