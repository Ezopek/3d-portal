# Handoff — Kategorie → tagi fasetowe (katalog)

**Dla:** agenta kodującego (Claude Code) · **Repo:** `3d-portal` · **Design:** `Katalog — Tagi fasetowe.dc.html` (7 makiet + stany brzegowe, PL/EN + light/dark)

Makieta jest źródłem prawdy dla wyglądu. Ten dokument opisuje **co** zmienić i **gdzie** w istniejącym kodzie.

---

## 1. Decyzja produktowa

Rezygnujemy z **twardej, pojedynczej kategorii** na rzecz **wielu tagów pogrupowanych w fasety**.

- Model może mieć dowolnie wiele tagów (relacja many-to-many już istnieje).
- Tag należy do jednej **grupy/fasety** (np. *Typ, Pomieszczenie, System, Materiał, Twórca*).
- Grupa to warstwa organizacyjna — w bazie tagi zostają płaską listą + pole `group`.
- **Tworzenie tagów: tylko admin.** Użytkownicy jedynie wybierają z gotowego zestawu.
- Łączenie w filtrze: **przełącznik AND/OR widoczny dla użytkownika** (domyślnie AND).
- **Migracja:** stare kategorie kasujemy; modele są tagowane od nowa (świadoma decyzja właściciela). Nie piszemy migracji danych kategorie→tagi.

---

## 2. Zmiany w modelu danych

### Backend (`apps/api`, SQLModel + Alembic)
- **Tag:** dodać `group: str | None` (slug fasety) + `group_position: int` do sortowania w obrębie grupy. Zostają `slug`, `name_en`, `name_pl`.
- **Nowy byt (opcjonalnie) `TagGroup`:** `slug`, `name_en`, `name_pl`, `position`. Alternatywa minimalna: trzymać grupy jako enum/tabelę słownikową. Rekomendacja: lekka tabela `TagGroup`, bo admin ma nią zarządzać (rename, kolejność).
- **Model:** usunąć `category_id` (kolumna + FK). Zostaje relacja `model_tags` (many-to-many).
- **Category / CategoryNode / CategoryTree:** usunąć tabele, endpoints i typy.
- Alembic: migracja usuwa `category`, `model.category_id`; dodaje `tag.group*` (+ `tag_group`).

### Frontend typy (`apps/web/src/lib/api-types.ts`)
- `TagRead`: dodać `group: string | null` (+ ewentualnie `group_position`).
- `ModelSummary` / `ModelDetail`: usunąć `category_id` i `category: CategorySummary`.
- Usunąć `CategorySummary`, `CategoryNode`, `CategoryTree`.

---

## 3. Zmiany w API

- **GET `/api/models`** — usunąć `category_ids`; dodać:
  - `tag_ids: string[]` (już jest do filtrowania po tagach),
  - `tag_match: "all" | "any"` (AND vs OR, domyślnie `all`),
  - `untagged: bool` (tylko modele bez żadnego tagu — patrz makieta 08B).
  - Semantyka rekomendowana: **AND między grupami, OR wewnątrz grupy**; `tag_match` to nadrzędny override użytkownika (makieta 04).
- **GET `/api/tags`** — zwracać `group`; dodać `?with_counts=true` (liczba modeli per tag, do sidebaru i admina) oraz endpoint zbiorczy grup z licznikami.
- **Admin (`/api/admin/tags`)** — CRUD tagów + grup, **merge** (`POST /merge {from_id, into_id}` — przepina `model_tags`, kasuje duplikat), rename, move-to-group. Governance z makiety 06.
- Usunąć endpointy `/api/.../categories`.

---

## 4. Zmiany w UI (mapa plików `apps/web/src/modules/catalog`)

| Plik | Zmiana |
|---|---|
| `components/CategoryTreeSidebar.tsx` | **Zastąpić** `FacetSidebar` (zrobione — usunięty w story 47.1) — grupy zwijane, checkboxy (multi-select), licznik per tag. Zamiast drzewa kategorii → lista grup faset. Search po tagach na górze. Pseudo-faseta „Bez tagów" przypięta na dole (makieta 02, 03, 08B). |
| `components/FilterRibbon.tsx` | Dodać **pasek aktywnych chipów** (usuwalne) + **toggle AND/OR** (`tag_match`). Obecny TagPicker można zostawić jako alternatywne dodawanie, ale główny wybór przenosi się do sidebaru. Status/Source/Sort bez zmian (makieta 03). |
| `routes/CatalogList.tsx` | Usunąć `useCategoriesTree`, `expandCategoryIds`, `category_id`. Stan URL: `tag_ids`, `tag_match`, `untagged`. Reszta (paginacja, empty state) zostaje. Pusty wynik → CTA „Przełącz na OR / Wyczyść" (makieta 08D). |
| `hooks/useCategoriesTree.ts` | Usunąć. Dodać `useTagGroups()` (grupy + tagi + liczniki). `useTags` zostaje (z `group`). |
| `ui/custom/ModelCard.tsx` | Chipy tagów już są (`topTags`). Dodać stan **„Bez tagów"** — jeden przerywany ghost-chip zamiast pustego rzędu (makieta 08A). |
| `components/sheets/EditTagsSheet.tsx` | Picker **pogrupowany po fasecie**; usunąć ścieżkę „create tag" dla nie-adminów (makieta 06 lewa). Selected-chips u góry zostają. |
| Model detail (`routes/CatalogDetail.tsx` / panel) | Tagi renderowane **grupami po fasecie** (label grupy + chipy). Grupa bez tagu: ukryta dla usera, myślnik + inline „Dodaj" dla admina (makieta 05, 08C). Tag klikalny → katalog z prefiltrem. |
| `modules/admin/...` | Nowy ekran **zarządzania tagami/grupami**: lista per grupa, liczniki, rename, merge, wykrywanie duplikatów (makieta 06 prawa). |

---

## 5. Stany brzegowe (makieta 08)
- **Brak tagów w ogóle** — poprawny stan; model zostaje w katalogu, nie pasuje do żadnego filtra. Karta: ghost-chip „Bez tagów". Filtr `untagged=true` do triażu (ważne po migracji — wszystko startuje bez tagów).
- **Brak tagu danej grupy** — grupa nie renderuje się userowi; admin widzi myślnik + „Dodaj".
- **Pusty wynik (AND za wąski)** — EmptyState z akcjami „Przełącz na OR" / „Wyczyść filtry".

---

## 6. i18n (`locales/pl.json`, `en.json`)
- Usunąć klucze `catalog.filters.category`, `openCategories`, `a11y.allCategories` itd.
- Dodać: `catalog.filters.facets`, `matchAll`/`matchAny`, `untagged`, `noTags`, `catalog.tags.groupless`, admin: `tags.merge/rename/newGroup/duplicates`.
- Tagi i grupy dwujęzyczne przez `name_pl` / `name_en` (jak dziś). UI-chrome przez i18next.

## 7. Dark mode
Tokeny `--color-*` są theme-aware (`.dark` w `styles/theme.css`) — nowe komponenty **muszą** używać klas Tailwilnd na tokenach (`bg-card`, `text-muted-foreground`, `border-border`), zero inline hex. Wtedy dark działa automatycznie (w makiecie jest toggle Light/Dark do podglądu).

## 8. Proponowana taksonomia startowa (do edycji przez właściciela)
Zmapowana z obecnych kategorii (makieta 01):
- **Typ:** Dekoracje, Wazony, Pojemniki, Organizery, Figurki ruchome, Uchwyty, Oświetlenie, Meble, Klipsy, Gadżety, Etui, Doniczki
- **Pomieszczenie:** Kuchnia, Łazienka, Biurko, Dom, Auto, Zwierzęta, Ogród
- **System:** Gridfinity, Multiboard, Bin Shells
- **Zastosowanie:** Naprawy, Przechowywanie, Elektronika, Lutowanie, Wkładki, Kalibracja
- **Drukarka:** K1 Max, Akcesoria
- **Materiał:** PLA, PETG, PCTG, TPU
- **Twórca (premium):** Jarek, …
- **Poziom:** Premium

## 9. Decyzje (rozstrzygnięte 2026-07-16 przez właściciela)
Wcześniej otwarte pytania — teraz zatwierdzone domyślne. Wszystkie ciągną w jedną stronę: **grupa to realny, adminowalny byt, nie konwencja-na-stringu**.

1. **Globalny search tagów w sidebarze — TAK**, ale tani: substring-match po `name_pl`/`name_en` **po stronie klienta**, na już pobranym `useTagGroups`. Bez nowego endpointu, bez fuzzy. (makieta 02)
2. **Twórcy — osobna faseta**, zero prefiksów tagów. „Twórca (premium)" i „Poziom" to po prostu kolejne grupy w `tag_group`. Prefiksy odrzucone jako powrót do grupowania-na-stringu, które ta zmiana eliminuje.
3. **Grupy rozwinięte domyślnie — 2 pierwsze wg `position`** (główne osie: *Typ*, *Pomieszczenie*) **+ każda grupa z aktywnym filtrem**; reszta zwinięta. Stan zwinięcia zapamiętany **per user w `localStorage`**. Liczba „ile rozwiniętych" jako stała/konfig, do podkręcenia bez zmiany logiki.
4. **`TagGroup` — TABELA** (`tag_group`), nie enum. Powód: admin ma zarządzać grupami (rename, kolejność — makieta 06), dwujęzyczność `name_pl`/`name_en`. Relacja: `tag.group_id` jako **nullable FK** → `tag_group.id` (nullable jest wymagane dla tagów bez grupy / pseudo-fasety „Bez tagów" — edge case 08).

## 10. Uwaga techniczna do migracji (weryfikacja w kodzie)
`Model.category_id` w `apps/api/app/core/db/models/_entities.py` to obecnie **NOT NULL + FK `category.id` ondelete=RESTRICT** (indeksowane). Zdjęcie kategorii to **nie** proste `drop column` — Alembic musi najpierw poluzować/usunąć FK i constraint NOT NULL, a `Category` jest **drzewem** (`parent_id` self-ref RESTRICT), więc kasowanie tabel idzie od liści. Wszystkie istniejące modele mają dziś ustawione `category_id` — po migracji startują bez żadnego tagu (świadomy reset, patrz sekcja 1 + filtr `untagged` z 08B).
