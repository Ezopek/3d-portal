# Portal UI Rewrite — Design Spec

**Date:** 2026-05-05
**Status:** Draft, pending user review
**Author:** Claude Opus 4.7 (brainstorming session with Michał)
**Scope:** Replace the catalog frontend so it consumes the new `/api/*` source-of-truth surface (delivered in spec `2026-05-04-portal-source-of-truth-design.md`) and exposes admin curating panels for Michał. The legacy `/api/catalog/*` router stays untouched in the backend; UI cuts over fully in one PR. Member-role login is wired up read-only (foundation for future favorites/orders, not built here).

---

## 1. Goal, non-goals, glossary, architecture

### 1.1 Goal

Stop the frontend from depending on the legacy `/api/catalog/*` routes and the
flat `Model` shape. Bring the UI in line with the new SoT entities (hierarchical
categories, tag entities, multi-kind notes, prints with photos, per-kind files,
external links, audit log) and add the admin curating affordances Michał needs
to maintain the catalog without dropping into the API directly. Prepare the
shell to receive members (read-only) so non-admin household/family accounts can
browse, with future-proofing for favorites/orders.

### 1.2 Goals (in scope)

- **Cutover** — every screen consumes `/api/*` directly. After this rewrite ships, the only client of `/api/catalog/*` is no client.
- **Hybrid catalog list** — collapsible category tree sidebar + always-visible filter ribbon, server-side pagination from day one.
- **Product-style detail** — gallery (4:3, ~36% width) + content rail (description / external links / metadata) + secondary tabs (Files, Photos admin, Prints, Operational notes, Activity admin).
- **Photos manager** (admin-only tab) — master-detail with `@dnd-kit/sortable` reorder, set-thumbnail, drag-drop upload.
- **Curating side-sheet pattern** — drawer-from-right (mobile: bottom sheet) for every multi-field edit. Popover for atomic edits. Modal only for destructive confirmation. Full page route only for "Create new model".
- **Role-aware UI** — `currentUser.role` propagated through context; member view hides Photos/Activity tabs, all ✏ icons, all "+ Add" buttons.
- **i18n preserved** — `pl.json` / `en.json` extended for new copy; per-content multi-lang fields (`name_*`, `description_*`, `body_*`) display by `i18n.language` with fallback.
- **Visual regression rebaseline** — every new screen has a Playwright snapshot.

### 1.3 Non-goals (deferred)

- **Member-driven curating** — favorites, wishlist, personal notes, ratings. No member-only screens or routes are added. The data model and component boundaries are kept extensible (per-component role checks, not separate "member app") so favorites/orders can be added later without ripping the shell apart.
- **Print queue / orders** — sibling v2 module slot. No FE work in this rewrite.
- **Filament/cost calculation** — separate brainstorm.
- **Self-signup** — admin manually provisions members via `POST /api/admin/users`.
- **Bulk admin operations** — agents handle bulk; UI is per-model.
- **Tag merge / category tree management UI** — both exist in admin API but admin-from-UI is out of scope (low frequency, agents do this).
- **Audit log filtering / search** — `ActivityTab` shows the per-model feed only; global audit search is out.

### 1.4 Glossary

- **Admin** — `User.role = admin`, full UI permissions, sees every ✏ and admin-only tab.
- **Agent** — `User.role = agent`, has API token, no UI flow (uses `/api/auth/login` programmatically). Identified in audit log alongside admin.
- **Member** — `User.role = member`, read-only catalog browse + share-link consumption. Provisioned by admin.
- **Anonymous** — no token, only `/share/$token` route accessible.
- **Side-sheet** — drawer-from-right on desktop, full-height bottom sheet on mobile. Primary edit surface.
- **Atomic edit** — one-click edit (status pill, rating ★, set-thumbnail). Implemented as popover, not sheet.
- **Curating** — all admin actions on a single model (description, tags, prints, photos, files, notes, external links).
- **Cutover PR** — the moment the UI stops calling `/api/catalog/*`. Backend legacy router remains live for two-week cooldown, then removed in a follow-up PR (the "formal cutover" item from `docs/operations.md`).

### 1.5 Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│ apps/web (React 19 + Vite + TanStack Router + Query)        │
│                                                              │
│  AuthGate (provides AuthContext { user, role })             │
│  └── AppShell                                                │
│      ├── TopBar (search? lang, theme, user menu)            │
│      ├── ModuleRail (catalog active; queue/spools/etc stub) │
│      └── route outlet                                        │
│          ├── /catalog          → CatalogList (hybrid)       │
│          ├── /catalog/$id      → CatalogDetail (product)    │
│          ├── /admin/models/new → CreateModelPage (admin)    │
│          ├── /share/$token     → ShareView (public subset)  │
│          └── /login            → LoginPage                  │
└─────────────────────────────────────────────────────────────┘
            │  fetch /api/*  (Bearer JWT for authenticated)
            ▼
┌─────────────────────────────────────────────────────────────┐
│ apps/api (FastAPI)                                          │
│  /api/auth/login, /api/auth/me                              │
│  /api/categories, /api/tags                                 │
│  /api/models, /api/models/{id}, /api/models/{id}/files      │
│  /api/models/{id}/files/{fid}/content (binary)              │
│  /api/admin/* (admin & agent only)                          │
│  /api/share/{token} (public)                                │
│  /api/catalog/* (legacy, untouched until follow-up)         │
└─────────────────────────────────────────────────────────────┘
```

State boundaries:
- **Server state**: TanStack Query, key per resource (`["models", filters]`, `["model", id]`, `["files", modelId, kind]`, etc.). Mutations invalidate keys.
- **URL state**: TanStack Router search params for catalog filters (category_id, tag_ids, status, source, q, sort, page).
- **sessionStorage**: category tree expand state, last-used filters fallback.
- **React Context**: `AuthContext` (current user + role) provided by `AuthGate`, consumed by every component making admin decisions.

---

## 2. User & auth model

### 2.1 Roles

- `admin` — Michał. One account today (provisioned by `bootstrap-admin` infra). Sees everything.
- `agent` — service-account, no UI login flow. Created by `scripts.bootstrap_agent`. UI does not authenticate as agent (the FE `LoginPage` accepts admin/member only).
- `member` — household/family browse-only. Provisioned by admin via `POST /api/admin/users` (endpoint to be added if missing — confirmed in implementation plan).

### 2.2 What the UI gates on role

| Surface | admin | member | anon |
|---|---|---|---|
| Login page | yes (full) | yes (full) | yes |
| Catalog list | yes | yes | redirect to login |
| Catalog detail (read) | yes | yes | redirect to login |
| Share view (`/share/$token`) | yes | yes | yes |
| Files tab (download STL) | yes | yes | yes (in share) |
| Photos tab | **yes** | **hidden** | hidden |
| Prints tab (read) | yes | yes | yes (in share) |
| Operational notes (read) | yes | yes | yes (in share) |
| Activity tab | **yes** | **hidden** | hidden |
| All ✏ edit affordances | **yes** | **hidden** | hidden |
| "+ Add print/note/file" | **yes** | **hidden** | hidden |
| `/admin/*` routes | yes | redirect to /catalog | redirect to /login |

### 2.3 Login flow

`POST /api/auth/login` → JWT cached in localStorage (current pattern). On every protected route, `AuthGate` calls `GET /api/auth/me` once, caches the result in `AuthContext`. Components import `useAuth()` to read `{ user, role, isAdmin }`. Role is stable per session — no re-fetch needed.

### 2.4 Member provisioning

UI scope: a small "+ Add member" dialog accessible from a hidden admin route (`/admin/users` — minimal — list of users with role + add member button). Form: email + display name + initial password (auto-generated if blank, shown once). Backend: `POST /api/admin/users` (to add) — single endpoint, enforces `role = member` (admin/agent created via scripts only). Out of scope for this rewrite: edit role, deactivate, password reset (admin can hit DB or use a script).

### 2.5 Token storage

Status quo (`localStorage`). Refresh: token has 30-min lifetime; `AuthGate` watches for 401 and pops a "Session expired — please log in again" toast plus redirect. No silent refresh in this rewrite (deferred to a future auth hardening pass).

---

## 3. Page layouts

### 3.1 List view (`/catalog`)

**Hybrid layout, mockup `list-layout.html`, choice C.**

- **Left sidebar (desktop ≥ lg)** — `CategoryTreeSidebar`. Recursive tree from `GET /api/categories` (single request, full tree). Each node shows count of models in that subtree. Expand/collapse state persisted in sessionStorage by category slug. "All · N" pseudo-row at top resets selection. Click on category → URL `?category_id=<uuid>`. Sidebar collapsible via toggle button (default expanded).
- **Mobile** — sidebar lives in a `Sheet` triggered by hamburger button in `TopBar` (or in filter ribbon). Behaves identically once open.
- **Top filter ribbon (always visible)** — `FilterRibbon`. Components: search input (full-text `q`), tag chips (multi-select; clicking a chip toggles `tag_ids` URL list; "+ tag" button opens popover with searchable `useTags(q)`), status select, source select, sort dropdown.
- **Grid** — responsive 2/3/4/5 columns at `sm/md/lg/xl`. Cards from `ModelCard` (refreshed for new shape).
- **Pagination** — server-side. Default `limit=48`. Page navigation at bottom (`Prev/Next` + page count). URL `?page=N` (1-indexed). Going to detail and back preserves URL state automatically (TanStack Router).

**Edge cases:**
- Loading: skeleton grid (24 placeholder cards).
- Error: `EmptyState` with "Network error — retry" button.
- No results: `EmptyState` with "Clear filters" action when filters active, otherwise "No models yet" copy.

### 3.2 Detail view (`/catalog/$id`)

**Product-style layout, mockup `detail-layout-v3.html`.**

- **Hero bar (full width)** — breadcrumb (`All › Decorations › Vases`, ✏ to edit category for admin) → title → meta-line (status pill, rating ★, source chip, top tags + "+N tags" overflow + ✏ for tag picker) → actions (`Share` button, `⋮` overflow with admin-only entries: Delete, Restore from soft-delete, View audit). On mobile this whole strip stacks vertically. *Note: a future "Print this" CTA (queueing a print) is anticipated and the actions slot is sized for it, but the button is not built in this rewrite.*
- **Main grid `36% / 64%` (desktop)** — collapses to single column at `< md`.
  - **Left**: Gallery. Main image 4:3, max-height bound. Thumbnail strip (7 visible + "+N" overflow) below. Click thumbnail = swap main. Source: `usePhotos(modelId)` returns `kind=image` ∪ `kind=print` ordered by `position` (server-stored).
  - **Right (content rail)**: three sections stacked.
    1. `DescriptionPanel` — primary text. Tabs `Description / View source ▾` (source collapsed by default; click expands inline). ✏ icon top-right opens `EditDescriptionSheet`. Multi-lang: shows `description_<lang>` with fallback.
    2. `ExternalLinksPanel` — list of `model.external_links`, each row `↗ url · source-pill`. Admin gets ✏/🗑 hover icons + "+ Add link" button.
    3. `MetadataPanel` — compact key/value grid: source, date added, file count by kind, print count.
- **Secondary tabs (full width below grid)** — `Files (N) | Photos (N) ✏admin | Prints (N) | Operational notes (N) | Activity ✏admin`. The `✏` glyph next to admin-only tabs visually marks them in admin view (member doesn't see these tabs at all).

**Tab contents:**

| Tab | Content | Admin extras |
|---|---|---|
| Files | List of `kind=stl` files by default. Filter chips: `STL · N` (active), `Source · N`, `Archive (3MF) · N`. Each row: icon, filename, size, ⬇ download. **Image/print kinds are deliberately excluded — they live in Photos.** | ✏ edit-row (rename, change kind), 🗑 delete-row, "+ Upload file" button (only `kind=stl/source/archive_3mf` here) |
| Photos | Master-detail. Left: photo list (40px thumb + name + meta + position #N + drag handle ⋮⋮). Right: detail panel — header (filename, kind, size, dimensions, uploader, "★ thumbnail" flag) + actions (★ Set as thumbnail, 🗑 Delete) + preview (4:3, max-height ≈220px). DnD reorder via `@dnd-kit/sortable`. Drag-drop upload zone below list. | (this whole tab is admin-only) |
| Prints | Cards of `ModelPrint`. Each card: 80px square thumb (1st linked photo, "1/N" overlay) + meta column (date, ★ rating, filament/printer/layer/flags pills, note text). | "+ Add print" (sheet), per-card ✏/🗑 |
| Operational notes | Cards by `NoteKind`. Operational = orange border, ai_review = blue, other = gray. Multiple notes per kind allowed. | "+ Add note" (sheet w/ kind selector), per-card ✏/🗑 |
| Activity | Audit log feed for this model. Filtered: `entity_type IN (model, model_file, model_print, model_note, model_external_link, model_tag)` AND `entity_id_chain` references this model. Each row: action pill (create/update/delete with color), short description, actor + relative time. | (this whole tab is admin-only) |

**Edge cases:**
- Soft-deleted model: header shows red banner "This model is soft-deleted (since DATE)" + admin gets "Restore" button. All edit affordances disabled while deleted.
- Loading: skeleton hero + skeleton tab content.
- 404: dedicated route guard with "Model not found — back to catalog" link.

### 3.3 Share view (`/share/$token`)

Public subset of detail view. Hits `GET /api/share/{token}` (existing endpoint; backend may need to return the new shape — confirmed in implementation plan).

Shows:
- Hero bar (no breadcrumb edit, no actions menu, only "Open share" if you want a direct link copy)
- Gallery (no admin tab)
- DescriptionPanel (no ✏, no source toggle — admin's description only)
- ExternalLinksPanel (read-only)
- MetadataPanel (read-only, source + date + counts)
- Secondary tabs: Files (download STL), Prints (read-only), Operational notes (read-only)
- Hidden: Photos tab, Activity tab, all edit affordances

**Privacy:** photos that the admin marks as "private" (a `private: bool` flag on `ModelFile`? — check whether SoT spec includes this; if not, treat all kind=image/print as public for share). For this rewrite, share view shows all photos; admin-flagged-private is **out of scope** unless trivially derivable.

### 3.4 Login (`/login`)

Existing screen kept structurally. Cosmetic refresh to align with new visual. Email + password; on success → `/catalog`. Member sees same form, role determined server-side, redirect path identical (catalog).

### 3.5 Create new model (`/admin/models/new`)

**Full-page route (the only one that escapes the side-sheet pattern).**

Wizard or single long form (decided in implementation plan after seeing actual API surface). Fields (in order):
1. Name (`name_en`, `name_pl`)
2. Category picker (tree-search modal, returns `category_id`)
3. Tags multi-select (with create-new)
4. Source enum + optional source_url
5. External links (zero or more rows)
6. Description (rich text, EN+PL tabs)
7. Files upload (multipart, drag-drop, auto-classifies kind by extension; admin can override per file)
8. Status (default `not_printed`), rating (optional)

Submit → `POST /api/admin/models` + per-file `POST /api/admin/models/{id}/files` (sequential because file uploads need `model_id`). Success → redirect to `/catalog/{new_id}`. Error → keep state, show errors per field.

This route is hidden from member; `AuthGate` denies it with redirect to `/catalog`.

---

## 4. Edit pattern reference

**Mockup: `edit-pattern.html`, choice B (side-sheet).**

### 4.1 Side-sheet (primary)

Shadcn `Sheet` from `@radix-ui/react-dialog` (already in the project). Slides from right on desktop, bottom on mobile.

Used for: edit description, edit tags, edit category, add/edit print, add/edit note, edit external link, edit file metadata, add file (within Files tab).

Structure of every sheet:
```
┌────────────────────────────────────┐
│ Header  [Title]              [✕]   │
│ ────────────────────────────────── │
│ Form fields (vertical)              │
│ ...                                 │
│ ────────────────────────────────── │
│ Footer  [Cancel] [Save]             │
└────────────────────────────────────┘
```

Width: `420px` desktop, full-width mobile. Footer sticky if content scrolls.

On submit:
1. Disable Save button + show spinner
2. Call admin mutation hook
3. On success: invalidate relevant queries + `toast.success` + close sheet
4. On error: `toast.error(message)` + keep sheet open + keep state

### 4.2 Popover (atomic)

Used for: status pill, rating ★ picker, single-tag toggle on existing chips, set-thumbnail (from Photos tab — alternative to ★ button in detail panel).

Shadcn `DropdownMenu` or `Popover` from `@radix-ui/react-dropdown-menu` (in project). Single click → option list → click → optimistic update + invalidate.

### 4.3 Confirmation modal (destructive)

Used for: delete model (soft), hard delete model (admin-only, separate flag), delete file, delete print, delete note, delete external link.

Shadcn `Dialog` (modal), centered, blocks. Body: red-toned text "This will [action]. [Consequence]." Footer: `Cancel` (gray) + `Delete` (red).

For **delete model**, require typing the model name to confirm (matches GitHub destructive-action pattern). For other deletes, single click on red button is enough.

### 4.4 DnD reorder

`@dnd-kit/sortable` (~6 KB gz). Touch sensors enabled. Used in Photos tab (reorder gallery position).

---

## 5. Component model

### 5.1 New components

```
apps/web/src/
├── shell/
│   └── AuthContext.tsx        ← new — provides { user, role, isAdmin, isMember }
├── lib/
│   ├── api.ts                 ← unchanged shape, used by all hooks
│   └── auth.ts                ← extend with useAuth() reading AuthContext
├── modules/catalog/
│   ├── components/
│   │   ├── CategoryTreeSidebar.tsx    ← new (replaces CategorySidebar)
│   │   ├── FilterRibbon.tsx           ← new (replaces FilterBar)
│   │   ├── ModelCard.tsx              ← refresh (UUID id, thumbnail FK)
│   │   ├── ModelHero.tsx              ← new
│   │   ├── ModelGallery.tsx           ← new (carousel)
│   │   ├── DescriptionPanel.tsx       ← new
│   │   ├── ExternalLinksPanel.tsx     ← new
│   │   ├── MetadataPanel.tsx          ← new
│   │   ├── SecondaryTabs.tsx          ← rebuild from ModelDetailTabs
│   │   ├── tabs/
│   │   │   ├── FilesTab.tsx           ← rebuild
│   │   │   ├── PhotosTab.tsx          ← new (admin-only)
│   │   │   ├── PrintsTab.tsx          ← rebuild
│   │   │   ├── OperationalNotesTab.tsx ← new
│   │   │   └── ActivityTab.tsx        ← new (admin-only)
│   │   └── sheets/
│   │       ├── EditDescriptionSheet.tsx
│   │       ├── EditTagsSheet.tsx
│   │       ├── EditCategorySheet.tsx
│   │       ├── AddPrintSheet.tsx
│   │       ├── EditPrintSheet.tsx
│   │       ├── AddNoteSheet.tsx
│   │       ├── EditNoteSheet.tsx
│   │       ├── EditExternalLinkSheet.tsx
│   │       ├── EditFileMetadataSheet.tsx
│   │       └── AddFileSheet.tsx
│   ├── hooks/
│   │   ├── useModels.ts        ← rewrite (server filters)
│   │   ├── useModel.ts         ← rewrite (full embed)
│   │   ├── useFiles.ts         ← rewrite (kind filter)
│   │   ├── usePhotos.ts        ← new (image+print, ordered)
│   │   ├── useCategoriesTree.ts ← new
│   │   ├── useTags.ts          ← new
│   │   ├── useAuditLog.ts      ← new (per-entity)
│   │   ├── useAuth.ts          ← new (consumer of AuthContext)
│   │   └── mutations/
│   │       ├── useUpdateModel.ts
│   │       ├── useDeleteModel.ts (soft + hard variants)
│   │       ├── useUploadFile.ts
│   │       ├── useUpdateFile.ts
│   │       ├── useDeleteFile.ts
│   │       ├── useReorderPhotos.ts (used by DnD)
│   │       ├── useSetThumbnail.ts
│   │       ├── useReplaceTags.ts
│   │       ├── useCreatePrint.ts
│   │       ├── useUpdatePrint.ts
│   │       ├── useDeletePrint.ts
│   │       ├── useCreateNote.ts
│   │       ├── useUpdateNote.ts
│   │       ├── useDeleteNote.ts
│   │       ├── useCreateExternalLink.ts
│   │       ├── useUpdateExternalLink.ts
│   │       ├── useDeleteExternalLink.ts
│   │       └── useCreateModel.ts
│   ├── routes/
│   │   ├── CatalogList.tsx          ← rewrite
│   │   ├── CatalogDetail.tsx        ← rewrite
│   │   ├── ShareView.tsx            ← rewrite (subset of detail)
│   │   └── CreateModelPage.tsx      ← new
│   └── types.ts                     ← regenerate (or hand-write) matching Pydantic responses
└── routes/
    ├── admin/
    │   ├── models/
    │   │   └── new.tsx              ← new TanStack route → CreateModelPage
    │   └── users.tsx                ← new (minimal: list members + add member dialog)
    ├── catalog/
    │   ├── index.tsx                ← unchanged shape, points at new CatalogList
    │   └── $id.tsx                  ← unchanged shape, points at new CatalogDetail
    └── share/
        └── $token.tsx               ← unchanged shape, points at new ShareView
```

### 5.2 Removed / repurposed

After rewrite ships:
- `CategorySidebar.tsx` — deleted
- `FilterBar.tsx` — deleted (replaced by `FilterRibbon`)
- `InfoTab.tsx` — deleted (rolled into DescriptionPanel + MetadataPanel + ExternalLinksPanel)
- `ModelDetailTabs.tsx` — deleted (replaced by SecondaryTabs)
- `types.ts` (old `Model` + `ModelListItem` + flat enums) — replaced by new types matching new API
- `galleryCandidates.ts` — review (logic moves into `usePhotos` likely)

### 5.3 Existing components kept

- `AppShell`, `TopBar`, `ModuleRail`, `AuthGate`, `ThemeProvider`, `LangProvider`, `LangToggle`, `ThemeToggle`, `UserMenu`
- `ui/*` shadcn primitives (button, card, dialog, dropdown-menu, input, select, separator, sheet, tabs, tooltip, badge)
- `ui/custom/StatusBadge`, `ui/custom/EmptyState`, `ui/custom/CardCarousel`, `ui/custom/Gallery`, `ui/custom/SourceBadge` — review and adapt as needed
- `ShareDialog` — adapt to call new admin endpoint shape

---

## 6. API integration & cutover

### 6.1 Endpoints consumed

Already existing (from SoT slices):
- `GET /api/categories` → tree (`CategoryTree`)
- `GET /api/tags?q=&limit=` → list
- `GET /api/models?category_id=&tag_ids=&status=&source=&q=&offset=&limit=&sort=` → paginated list
- `GET /api/models/{id}` → full embed (with files, prints, notes, external_links)
- `GET /api/models/{id}/files?kind=` → files
- `GET /api/models/{id}/files/{fid}/content` → binary stream (already has ETag)
- `GET /api/share/{token}` → public model view (verify response shape uses new schema)
- `POST /api/auth/login`, `GET /api/auth/me` (verify `me` returns `role`)
- `POST/PATCH/DELETE /api/admin/models/...` and sub-resources (already shipped in 2C)

Confirm-or-add list (verify in implementation plan):
- `GET /api/auth/me` returning `role` field — if missing, add in slice 3A
- `POST /api/admin/users` for member provisioning — likely missing, add in slice 3F
- `GET /api/admin/users` for the user list page — add in slice 3F
- `POST /api/admin/photos/reorder` (or similar) for batch DnD reorder of photo positions — add in slice 3D
- `GET /api/admin/audit-log?entity_type=&entity_id=` for ActivityTab — add in slice 3E if missing

### 6.2 Cutover strategy

1. **Single big PR** (`feat/sot-slice-3*`) cuts the FE over to `/api/*`. Backend `/api/catalog/*` left running.
2. **Two-week observation window** post-deploy. Watch logs on `.190` for any `/api/catalog/*` requests. None should appear (only stale browser tabs would hit it).
3. **Cleanup PR** (separate, `chore/remove-legacy-catalog-router`): remove `/api/catalog/*` routes + tests. This is the "formal cutover" listed in `docs/operations.md`.

### 6.3 State management

| State | Storage | Lifetime |
|---|---|---|
| Server cache | TanStack Query in-memory | Session (cleared on logout) |
| Auth (token) | localStorage | Persisted; cleared on logout/expiry |
| Current user (id, role, email) | React Context via AuthGate | Session |
| Catalog filters | URL search params (TanStack Router) | URL-bound |
| Last-used filters fallback | sessionStorage `catalog:last-filters` | Session (existing pattern) |
| Category tree expand state | sessionStorage `catalog:tree-expand` | Session |
| Sheet open state | Local component state | Component lifetime |
| DnD photo order during drag | Local component state, optimistic | Until drop committed |

---

## 7. Internationalization

`i18next` with `pl.json` / `en.json`. Existing pattern maintained. New keys added under namespaces:

```
catalog.tabs.{files, photos, prints, operationalNotes, activity}
catalog.actions.{addPrint, addNote, addFile, addLink, setThumbnail, ...}
catalog.empty.{prints, notes, files, photos}
catalog.activity.action.{create, update, delete}
admin.users.{title, addMember, ...}
errors.network, errors.unauthorized, errors.notFound
```

### 7.1 Multi-lang content fields

Backend stores `name_en`/`name_pl`, `description_en`/`description_pl`, `body_en`/`body_pl`. Frontend renders `field_<i18n.language>` with fallback to the other lang if empty (`name_pl ?? name_en`). Edit sheets show two tabs (PL / EN) for any multi-lang field; admin can leave one empty.

Source description (the original from Printables/etc.) is stored separately on `Model` (likely `source_description_en` or as a special `ModelNote`; resolved in implementation plan). UI shows admin-edited description by default; "View source ▾" expander reveals the source text read-only.

---

## 8. Testing strategy

### 8.1 Unit (vitest + React Testing Library)

- One test file per new hook covering happy path + error path + filter param handling.
- One test file per new component covering: rendering with props, role-aware conditional rendering (`as=admin` vs `as=member`), interactive flow (open sheet → submit → mutation called).
- Custom render helper extending current pattern: `renderWithProviders(ui, { user: AdminFixture | MemberFixture | null })` — mocks `AuthContext`.

### 8.2 Visual regression (Playwright)

Rebaseline every screen affected. New baselines for:
- Catalog list (admin view, member view, mobile, empty state)
- Catalog detail per tab × role × empty/populated × mobile
- Photos tab states (no photos, 1 photo, 12 photos, dragging, master-detail with selection)
- Sheets (one snapshot per sheet at default state)
- Confirmation modal
- Share view
- Login page (refreshed)
- Create model page

Run `npm run test:visual` from `apps/web/` per AGENTS.md. Snapshots committed under `apps/web/tests/visual/__snapshots__/`.

### 8.3 Integration (vitest + MSW)

- Login → role-aware redirect
- Filter ribbon → URL update → query refetch
- Edit description sheet → submit → query invalidation → updated UI
- Add print sheet with photo upload → multipart submit → photo appears in PhotosTab + count updates
- Photos DnD → reorder mutation → query invalidation → ModelGallery in hero shows new order
- Member view → no admin tabs visible, no ✏ icons
- 401 response → toast + redirect to login

### 8.4 Accessibility

- `axe-core` smoke test on each page route (one snapshot test per route to catch obvious failures).
- Manual checklist before merge: keyboard nav through filter ribbon, keyboard reorder for DnD photos (arrow keys), focus trap in sheets, focus restore on sheet close, aria labels on ✏ buttons.

---

## 9. Implementation slicing

| Slice | Goal | Branches off |
|---|---|---|
| **3A — Auth + API context** | `AuthContext`, `useAuth`, `currentUser` propagated. New `lib/api.ts` types regenerated/hand-written for new endpoints. `GET /api/auth/me` returns role (verify or add). | `main` |
| **3B — List view rebuild** | `CategoryTreeSidebar`, `FilterRibbon`, server-side filters, server-side pagination, refreshed `ModelCard`. URL state preserved. Visual regression rebaseline for list. | `main` (after 3A) |
| **3C — Detail view (read-only)** | Hero, gallery, description/external/metadata panels, all secondary tabs (Files, Prints, Operational notes) in read-only mode. Admin sees same content as member but without edit affordances yet. Visual rebaseline. | `main` (after 3B) |
| **3D — Photos manager + DnD** | Admin-only PhotosTab with master-detail, `@dnd-kit/sortable` reorder, set-thumbnail, drag-drop upload, delete photo. Hero gallery now respects ordered position. | `main` (after 3C) |
| **3E — Edit affordances** | All side-sheets (description, tags, category, prints, notes, external links, files), confirmation modal for destructive, popovers for atomic, ActivityTab with audit log. | `main` (after 3D) |
| **3F — Create model + share view + member admin** | Full-page `/admin/models/new`, share view rewrite, `/admin/users` minimal (list + add member dialog), removal of dead code (`InfoTab`, `FilterBar`, `CategorySidebar`, old `types.ts`). Visual baseline final. | `main` (after 3E) |

Each slice = own brainstorm/plan/execution cycle (writing-plans → subagent-driven-development) per AGENTS.md. Each slice deploys to `.190` after merge per project memory. After 3F passes a two-week observation period, a separate cleanup PR removes `/api/catalog/*` from the backend.

### 9.1 Estimated effort

~70 commits total across 6 slices. Visual baselines change 3 times (3B, 3C, 3E final). Realistically 3-4 working sessions; each slice is one session.

---

## 10. Out of scope reminders (so we don't drift)

- No print queue / orders UI
- No filament cost calculator
- No member-write features (favorites, personal notes, ratings)
- No bulk operations (tag merge, category tree management — agent territory)
- No global audit log search
- No silent token refresh
- No self-signup
- No private-photo flag (assume all photos are share-visible)
- No multi-user comments
- No dark/light visual redesign — current theme tokens kept

These belong in future brainstorms when there's a concrete need.

---

## 11. Open questions resolved during brainstorm

- **Description model** — one admin-editable description per language per model, source archived separately and accessible via "View source ▾" toggle. Admin "translates" or rewrites freely.
- **Operational vs description split** — product behavior ("hard to walk in PLA", "TPU recommended", "easy to scale") goes in description. Print parameters (layer height, supports, infill, brim) go in operational notes.
- **Files tab default** — `kind=stl` only. Image/print kinds live in Photos tab. Source/3MF kinds toggleable via filter chips.
- **Photos preview size** — compact (~220px height, 4:3), not larger than the hero gallery preview.
- **Photos actions placement** — info + actions ABOVE preview, always visible without scroll.
- **DnD vs modal-reorder** — DnD on the list (`@dnd-kit/sortable` is small enough).
- **Member view scope** — read-only, no Photos/Activity tabs, no ✏, no add buttons. Future favorites/orders deferred.
- **Mobile ambition** — desktop-first, mobile-friendly responsive (every screen usable, photo upload uses camera).
- **Edit pattern** — side-sheet primary, popover atomic, modal destructive, full page only for create new model.

---

End of spec.
