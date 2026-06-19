---
artifact: correct-course
topic: profile-offers-as-estimate-source-of-truth
route: bmad-correct-course (party-mode workshop — PM/Analyst · Architect · UX · Dev)
date: 2026-06-19
status: ready-for-laura-review
controller: Laura/Hermes (ITCM)
scope: planning only — no application code touched this pass
baseline_commit: 43f0eb9 feat(admin) add profile policy backfill controls
supersedes_intent_of:
  - E39.x material-default / default-matrix backfill as the primary estimate driver
inputs_read:
  - apps/api/app/modules/slicer/profile_offer.py
  - apps/api/app/modules/slicer/profile_policy.py
  - apps/api/app/modules/slicer/profile_publish.py
  - apps/api/app/modules/slicer/matrix_backfill.py
  - apps/api/app/modules/slicer/resolver.py
  - apps/api/app/modules/slicer/{member_router,router,admin_router}.py
  - apps/web/src/modules/catalog/components/tabs/FilesTab.tsx
  - apps/web/src/modules/admin/ProfileOffersPage.tsx
  - _bmad-output/ux/stl-estimate-display-catalog-files-ux.md
---

# Correct-Course — Profile Offers jako jedyne źródło prawdy (SoT) dla estymat slicera

> **Workshop (party-mode).** Cztery role przeszły przez kod i evidence. Konsensus poniżej.
> Konflikt sprowadza się do jednego zdania: **oferta już niesie blok filamentu, więc
> `material_defaults` jest drugą, rozjechaną konfiguracją tego samego faktu** — i to ona
> (a nie oferta) blokuje backfill (`material_defaults_count=0 → cells_total=0`).

---

## 1. Problem statement

Istnieją **dwie równoległe ścieżki** wyznaczania „jakiego profilu filamentu użyć do estymaty":

| Ścieżka | Kod | Co robi | Status |
|---|---|---|---|
| **A — łańcuch oferty** (zamierzony produkt) | `profile_offer.py` + `resolve_chain(..., profile_selection=None)` + `profile_publish.publish_offer` | Oferta osadza pełny łańcuch *machine + process + **filament***. Publikacja **rozwiązuje łańcuch wprost z bloków biblioteki** → zapisuje `published_bundle_hash` na sidecar oferty i kolejkuje slice dla **jednego** wyznaczonego STL. Member czyta `GET /api/estimates?offer_id=…` → `published_bundle_hash` → `estimate_store.read(stl_hash, published_bundle_hash)`. | Działa i jest **kompletna** dla pojedynczego STL. |
| **B — macierz `material_defaults`** (pozostałość z ery grid/intent) | `profile_policy.py` (`material -> orca_filament_profile_ref`) + `matrix_backfill.py` (`published offers × enabled material_defaults`) | Backfill enumeruje iloczyn i dla każdej komórki woła `resolve_chain(chain, profile_selection=default_material_profile)`, co **przekierowuje** `inherit` bloku filamentu oferty na profil z `material_defaults` → **inny `bundle_hash`** niż `published_bundle_hash` oferty. | Generuje szum / pusty wynik. |

**Dlaczego dry-run E39.1 pokazuje `cells_total=0`:** `enumerate_matrix_cells` wymaga
niepustego `policy.material_defaults` **oraz** żeby klucz materiału był w
`compatible_material_categories` oferty (`matrix_backfill.py:101-108`). Przy
`material_defaults_count=0` iloczyn jest pusty → `cells_total=0` → `enqueued=0`. UI backfillu
nic nie robi, bo zależy od **drugiej** konfiguracji, której operator słusznie nie wypełnia —
skoro blok filamentu oferty już nazywa filament.

**Na czym polega duplikacja (odpowiedź na intencję #6/#7):**
- Łańcuch oferty **już** rozwiązuje się do konkretnego profilu filamentu — to dokładnie robi
  `publish_offer`, licząc `published_bundle_hash` **bez** żadnego `profile_selection`.
- Przekierowanie w ścieżce B **nadpisuje** własny blok filamentu oferty profilem z
  `material_defaults`. Stąd dwa wyniki, oba złe:
  - `material_default == filament bloku oferty` → ta sama wiązka co publikacja → czysta duplikacja;
  - `material_default != filament oferty` → estymaty **nie zgadzają się** z tym, co oferta deklaruje → mylące/błędne.
- Czyli: **domyślna oferta JUŻ dostarcza profil/filament.** Backfill pokazał 0, bo był
  podpięty pod starą macierz `offers × material_defaults`, a nie pod `offers × STLs` po
  `published_bundle_hash`.

---

## 2. Decision recommendation (jedna architektura)

**Rekomendacja: Profile Offer = SoT. `material_defaults` znika ze ścieżki produktowej estymat.**

1. **Oferta ma dokładnie jeden `published_bundle_hash`** wyprowadzony wyłącznie z własnego
   łańcucha (machine+process+**filament**), `profile_selection=None`. Blok filamentu w
   łańcuchu **JEST** filamentem. Żadnego `material_defaults` do estymat ofertowych. *(To już
   jest zachowanie `publish_offer` — nie trzeba go zmieniać; trzeba zmienić, co napędza
   recompute.)*
2. **Recompute = „policz estymaty dla każdego katalogowego STL względem `published_bundle_hash`
   każdej opublikowanej oferty".** Zastępujemy enumerację `offers × material_defaults`
   enumeracją `published offers × all catalog STLs`, biorąc gotowy `published_bundle_hash` z
   sidecaru (bez ponownego `resolve` — hash już jest zapisany). Ograniczenie kolejki:
   `offers × STLs`, **niezależne** od `material_defaults`.
3. **Odczyt estymaty member bez zmian** — `GET /api/estimates?offer_id=…` jest już oparty na
   `published_bundle_hash` i poprawny. Osobna lista ofert member
   (`GET /api/profiles/offers/published`) wymaga story 40.3, bo obecnie filtruje `published`,
   ale nie `visible`. Luka w estymatach: dziś estymaty istnieją tylko dla pojedynczego
   `published_stl_hash` z czasu publikacji; nowy recompute uzupełnia wszystkie STL-e.

**Czy `material_defaults` zostaje?** Tak — **zdemotowane do advanced/legacy**, nie wymagane.
Zachowuje jedną realną, opcjonalną niszę: **per-spool override**, gdy member przypina konkretny
Spoolman-filament inny niż domyślny filament oferty (ścieżka `filament_overrides` /
`exact_filament_mapping` po `spoolman_filament_ref`). To funkcja zaawansowana, **nie** warunek
działania estymat ofertowych. Kod policy zostaje; admin-UI (ProfilePolicyPanel + default-matrix
backfill) chowamy za flagą *advanced/debug*; główny przycisk „recompute" staje się ofertowy.

> Konsensus ról: PM — zgodne z intencją operatora i upraszcza model mentalny. Architect —
> żadnej migracji danych (store append-only, klucz `(stl_hash, bundle_hash)` niezmienny). UX —
> usuwa „drugą tajemną konfigurację". Dev — to głównie zmiana **enumeracji** + relabeling UI;
> niskie ryzyko.

---

## 3. Domain model correction (pod SoT = oferta)

| Pojęcie | Pole/kod | Znaczenie pod SoT |
|---|---|---|
| **visible** | `visibility == "visible"` | Oferta pojawia się w selektorze member/katalog. **Luka:** dziś `GET /profiles/offers/published` (member_router) filtruje tylko `publish_state=="published"`, **ignoruje** `visibility`. Pod SoT lista member musi honorować `visible`. |
| **default** | `is_default` | Oferta wstępnie zaznaczona w selektorze katalogu (per kategoria materiału). FilesTab ma wybrać `is_default` jako początkowy `selectedOfferId`. Walidacja `duplicate_default` już istnieje (widoczne oferty, wspólna kategoria). |
| **published** | `publish_state=="published"` + `published_bundle_hash` | Łańcuch rozwiązany → wiązka wybita → estymaty dają się odczytać. Niepublikowana = brak hasha = brak estymat. |
| **stale** | `sync_state=="stale"` (`derive_sync_state`) | Bloki łańcucha zmieniły się od publikacji (mismatch `published_chain_fingerprint`) **lub** publikacja sprzed fingerprintu. `published_bundle_hash` nie odzwierciedla już bieżącego łańcucha. |
| **republish / resync** | `POST …/offers/{id}/publish` (ponownie) | Przelicza `published_bundle_hash` z bieżącego łańcucha + ponownie kolejkuje estymaty → czyści `stale`. |
| **recompute / slice all STLs** | **NOWE** (ofertowe) | Kolejkuje estymaty dla `(każdy katalogowy STL × published_bundle_hash oferty)`, by każdy wiersz STL pokazał gramy dla oferty. Zastępuje macierz `material_defaults`. |

---

## 4. Legacy system disposition

| Element | Decyzja | Zabezpieczenie |
|---|---|---|
| FilesTab grid/intent `PrintIntentPresetSelector` (Material×Quality, tryb `useEstimate` preset) | **Usunięty z produktu** — `1bcfc09` już zdjął legacy selektor; FilesTab jest offer-first. Potwierdzić brak resztek preset-mode. | bez flagi — już zrobione |
| ProfilePolicyPanel (material defaults + default-matrix backfill UI) w ProfileOffersPage | **Schować za flagą advanced/debug**; główny recompute → ofertowy. | flaga FE; brak usuwania endpointu |
| `profile_policy.py` / `filament_overrides` / `matrix_backfill.py` | **Zostawić jako advanced** (nisza per-spool override). Nie usuwać kodu w tym przebiegu. | demota, nie delete |
| `resolver._apply_profile_selection` / seam `profile_selection` | Zostaje (używane tylko przez advanced/override path). Ścieżka publikacji oferty już go **nie** używa. | bez zmian |
| `resolve()` / intent-grid (`intents/` tree) | Demote do internal/legacy; sprawdzić, czy coś poza testami jeszcze woła. Pełne usunięcie = osobna story za flagą. | gate story 40.4 |

User akceptuje pełne usunięcie starego produktowego grid-flow **jeśli bezpieczne** — robimy to
etapowo (demote → flaga → osobna story usunięcia), nigdy hurtowo w jednym przebiegu.

---

## 5. Backend architecture

**Odczyt: wybrana oferta → bundle hash → estymata (BEZ ZMIAN, już poprawne):**
```
GET /api/estimates?stl_hash=<h>&offer_id=<id>
  → _read_published_offer_or_404 → publish_state_of(sidecar).published_bundle_hash
  → estimate_store.read(stl_hash, published_bundle_hash)
  → EstimateView (status: fresh|queued|stale|absent|failed|not_computed)
```

**Recompute/backfill estymat dla ofert (NOWE — rdzeń poprawki):**
- Nowa **czysta** enumeracja
  `enumerate_offer_cells(offers, *, visible_only: bool, offer_id: str | None = None)` → jedna
  komórka na opublikowaną ofertę, `bundle_hash = sidecar.published_bundle_hash` (żadnego
  `resolve` — hash gotowy). Pomija oferty bez hasha / `validation_state=="invalid"`.
- Jeśli operator poda `offer_id`: malformed/non-hex → **422 `invalid_offer_id`**;
  well-formed but missing → **404 `offer_not_found`**; oferta istnieje, ale nie kwalifikuje się
  do recompute (unpublished / brak `published_bundle_hash` / invalid / hidden przy
  `visible_only=true`) → **422 z reason_category** zamiast cichego pustego sukcesu.
- Reużyć `enqueue_matrix_for_all_stls(resolved_cells, …)` 1:1 (freshness pre-check +
  idempotentne kolejkowanie `(stl_hash, bundle_hash)`, liczniki już są).
- Nowy endpoint: `POST /api/admin/profiles/offers/recompute-estimates`
  - body: `{ dry_run: bool=True, offer_id: str|None=None, visible_only: bool=True, max_cells: int|None=None }`
  - response: ten sam kształt liczników co `DefaultMatrixBackfillResponse`
    (`inspected, cells_total, cells_resolved, would_enqueue, enqueued, already_fresh, missing_stl, errors`).
  - `max_cells`, gdy ustawiony, jest twardym preflight limitem `cells_total × inspected`;
    przekroczenie zwraca 422 przed enqueue. Domyślnie brak capu poza dry-run+confirm, bo system
    już ma freshness/dedup.
  - **To wprost naprawia `cells_total=0`:** przy N opublikowanych ofertach i M STL-ach, zero
    `material_defaults` → `cells_total=N`, `would_enqueue ≤ N×M − already_fresh`.

**Generowanie estymaty dla publikowanej/domyślnej oferty:**
- `publish_offer` już kolejkuje slice dla wyznaczonego STL przy publikacji (pozostaje). Obecny
  post-publish hook używa starej macierzy `material_defaults`; **40.1 implementuje replacement
  tego hooka** offer-driven hookiem (`offer_id=…`, `visible_only=false` lub ignorowane dla
  konkretnej oferty), żeby publikacja nie zostawiała operatora w stanie `cells_total=0`.
  Failure hooka nadal jest swallow+log, jak dziś — nie rollbackuje publikacji.
- Po publikacji/republish endpoint recompute ma być dostępny offer-scoped, by oferta miała
  estymaty dla **wszystkich** STL, nie tylko jednego. Zmiana `is_default` sama nie zmienia
  bundle_hash; jeśli brakuje estymat, admin odpala recompute.

**Migracja / kompatybilność:**
- Estymaty kluczowane `(stl_hash, bundle_hash)` zostają ważne. Recompute ofertowy celuje w
  `published_bundle_hash`, który może już mieć estymatę z publikacji single-STL → te liczą się
  jako `already_fresh`, reszta `enqueued`. **Brak migracji danych** (store append-only).
- Wiązki z macierzy `material_defaults` (jeśli jakieś powstały) zostają jako sieroty —
  nieszkodliwe, append-only; nie kasujemy.

---

## 6. Frontend UX

**Admin (ProfileOffersPage):**
- Główny przycisk recompute: **„Przelicz estymaty dla wszystkich STL (bieżące oferty)"** →
  `POST …/offers/recompute-estimates` (dry-run domyślnie, potem confirm). Wynik przez
  istniejący `BackfillSummary` (te same liczniki).
- Per-wiersz oferty: zachować resync/republish dla `stale`; po sukcesie zaproponować recompute
  offer-scoped.
- ProfilePolicyPanel (material defaults + matrix backfill) → za sekcją *Advanced* (collapsed,
  z notką „opcjonalne: per-spool override; nie wymagane do estymat ofertowych").

**Katalog (FilesTab) — już offer-first; doprecyzowania:**
- Selektor ofert: lista z `usePublishedOffers` **filtrowana do `visible`**; wstępny wybór =
  oferta `is_default` (per materiał), fallback pierwsza widoczna.
- Per-STL chip (`EstimateChip` + `useOfferEstimate`) — stany bez zmian:
  `loading` (spinner) · `absent`/`not_computed` („—", bez 0 g) · `fresh` (gramy) ·
  `stale` (gramy + amber) · `queued` (gramy + spinner) · `failed` („—" + alert) ·
  `network-error` („—" + alert, nieblokujące).
- Przełączenie oferty → przekluczowanie wszystkich wierszy (cache key `{offerId}`), ostatnia
  wartość przygaszona do czasu rozwiązania (bez pełnego skeletonu listy).
- Empty/loading/error listy ofert: brak widocznych ofert → komunikat „brak dostępnego profilu";
  błąd → inline + Retry (już w `PublishedOfferPicker`).

---

## 7. Implementation stories (małe, uporządkowane)

> Pełny spec pierwszej story: `_bmad-output/implementation-artifacts/40-1-profile-offer-estimate-sot.md`.

| Story | Tytuł | Zakres | Zależności |
|---|---|---|---|
| **40.1 (DEV-READY)** | Offer-driven estimate backfill (backend) | `enumerate_offer_cells` + `POST …/offers/recompute-estimates` (dry-run default) reużywające `enqueue_matrix_for_all_stls`. Naprawia `cells_total=0`. Tylko backend + pytest. | — |
| 40.2 | Admin: ofertowy recompute jako główny; ProfilePolicyPanel → Advanced | Relabel/przepięcie przycisku na nowy endpoint; schowanie policy panelu za flagą advanced. | 40.1 |
| 40.3 | Katalog: member-list honoruje `visible` + wybór `default` | Filtr `visibility=="visible"` w member published list + wstępny wybór `is_default` w FilesTab. | 40.1 |
| 40.4 (gated) | Demote/usunięcie legacy grid + material_defaults z produktu | Za flagą; potwierdzić brak żywych callerów; etapowo. | 40.1–40.3 + zgoda Laury |

**Bramki dla każdej story (AGENTS.md):** story branch; `ruff format --check`+`ruff check` (api);
`pytest` (api); `npm run lint/typecheck/test`; `npm run test:visual` przy zmianie UI;
external review (routine: Aider / `laura-aider-review-diff` per agent rulebook);
`infra/scripts/check-all.sh` zielone przed ff-merge; deploy po zielonym wg workflow.

---

## 8. Questions for Laura / User

**Brak twardych blokerów — proceed-ready.** Dwa punkty do potwierdzenia (przyjęte założenia,
można zacząć 40.1 bez odpowiedzi):

- **Z1 (założenie, nieblokujące):** member published list ma filtrować do `visibility=="visible"`
  (intencja #2). Przyjmujemy TAK. Jeśli „published, ale ukryte" ma jakieś istniejące zastosowanie
  — powiedz; inaczej idziemy z `visible`.
- **Z2 (założenie, nieblokujące):** `material_defaults`/`filament_overrides` zostają jako
  *advanced* (per-spool override), nie usuwane teraz. Jeśli operator chce je usunąć w całości —
  to 40.4 za flagą.
- **Z3 (założenie, nieblokujące):** recompute „wszystkie STL × wszystkie widoczne oferty" może
  być duży; przyjmujemy dry-run domyślnie + confirm + istniejący freshness pre-check jako limit
  eksplozji kolejki. 40.1 dopuszcza opcjonalny `max_cells` preflight cap, ale bez domyślnego
  twardego limitu dopóki operator nie poprosi.

## 9. Non-goals / safety

- **Brak cichego hurtowego usuwania na live.** Demote legacy = flaga/relabel, nie delete.
- **Brak destrukcyjnego usuwania legacy bez flagi / gate story** (40.4 jest osobno gate'owane).
- **Brak logowania sekretów / refów Orca w czysto.** Liczniki backfillu agregują, nie wyciekają.
- **Brak migracji danych** — store append-only, klucz `(stl_hash, bundle_hash)` niezmienny;
  istniejące estymaty i wiązki pozostają ważne.
- **Brak mutacji systemów live** w tym przebiegu planowania.
- Recompute domyślnie **dry-run**; realne kolejkowanie tylko po jawnym potwierdzeniu.
