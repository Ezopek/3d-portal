---
title: 'Story 12.2 — Admin Users default-hide inactive accounts + reveal toggle'
type: 'feature'
status: 'ready-for-dev'
created: '2026-05-21'
epic: 12
initiative: 7
story_id: '12.2'
story_key: '12-2-admin-users-inactive-filter'
predecessor_scp: '_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md (Initiative 7; SCP §4.1.1 + §4.3.1)'
realizes:
  - 'FR7-ADMIN-USERS-1 (full)'
  - 'NFR7-UX-1'
  - 'NFR7-A11Y-1 (checkbox keyboard reach)'
predecessor_commits:
  - '9ce0463 — Story 12.1 (admin invites unblock + responsive layout) 2026-05-21'
  - '313dd33 — Story 14.3 (visual baselines regen)'
  - '1d5f7a8 — Story 14.1 (vitest admin finder fixes + 52 i18n keys)'
auto_approval_directive: 'Operator standing approval per "lecimy do końca jak init 5". Status auto-flipped backlog → ready-for-dev.'
---

## Story 12.2 — Admin Users default-hide inactive accounts + reveal toggle

**As an** admin browsing /admin/users,
**I want** deactivated accounts hidden by default with an explicit reveal toggle,
**so that** the active user list isn't cluttered by deactivated accounts that operators rarely need to see.

### Acceptance Criteria

**AC-1 (FR7-ADMIN-USERS-1 — Backend):** `apps/api/app/modules/admin/router.py:list_admin_users` accepts an optional `is_active: bool | None = Query(default=None)` query param. When present, filter base_stmt + count_stmt by `User.is_active == is_active`. When absent, no filter (show all). **Verifiable:** GET `/api/admin/users?is_active=true` returns only `is_active=true` rows; `?is_active=false` returns only inactive; no param returns all.

**AC-2 (FR7-ADMIN-USERS-1 — Frontend):** `apps/web/src/modules/admin/UsersPage.tsx` adds an `is_active` filter state defaulting to `true` (hide inactive). A checkbox labeled `t("admin.users.filter_show_inactive")` toggles state to `null` (show all). Sub-controls:
- Checkbox renders below the page header, adjacent to the existing search box.
- Default unchecked → query passes `is_active=true`.
- Checked → query passes no `is_active` param (returns all).
- Checkbox state syncs to URL search param `show_inactive=1` via TanStack Router's search-param API so the toggle survives reloads + is shareable.

**AC-3:** Inactive rows when shown have a visually muted appearance:
- `<tr>` className gains `text-muted-foreground` AND `bg-muted/30` for `row.is_active === false`.
- The email column gets a strikethrough OR muted-italic style.
- Active rows render as today (no change).

**AC-4 (i18n):** Add two new keys to pl.json + en.json with parity:
- `admin.users.filter_show_inactive` = "Pokaż nieaktywne konta" / "Show inactive accounts"
- `admin.users.row_inactive_indicator` = "(nieaktywne)" / "(inactive)" — rendered as a small badge or sr-only label for screen readers.

**AC-5 (NFR7-A11Y-1):** Checkbox is keyboard-reachable via Tab. Activated by Space. Has `aria-label` resolving to the visible label text. Verified by ≥1 vitest test that uses `tab()` + `space` simulation.

**AC-6 (NFR7-UX-1):** Pre-CR agent-browser visual verification at desktop-default (1280×720) + mobile-light (390×844) viewports. Capture:
- Default state (checkbox unchecked) — no inactive users visible.
- Checked state — inactive rows show with muted style.
- Console clean (no errors).
- Snapshot attached to Dev Agent Record.

**AC-7 (tests):**
- Add 3+ pytest tests for backend `is_active` filter (true/false/null cases).
- Add 2+ vitest tests for frontend checkbox behavior (default state, toggle).
- Regen visual baselines for admin-users (4 projects × 3 states; checkbox + muted-row rendering changes the surface).

### Tasks

- [ ] T1 — Backend: extend `list_admin_users` signature with `is_active` Query param; apply WHERE clause; cover with 3 pytest tests.
- [ ] T2 — Frontend useState + URL search-param sync for `show_inactive` flag.
- [ ] T3 — Frontend checkbox UI below header.
- [ ] T4 — Frontend muted-row styling for inactive rows.
- [ ] T5 — i18n keys (PL/EN parity).
- [ ] T6 — Vitest tests (default state + toggle).
- [ ] T7 — Playwright baseline regen for admin-users.
- [ ] T8 — Agent-browser visual verify @ desktop + mobile.
- [ ] T9 — Lint + tsc + full vitest + pytest regression.
- [ ] T10 — Sprint-status flip + commit + deploy.

### Non-goals (NFR7-COMPAT-1 etc.)

- No new admin auth boundary changes (still `current_admin`).
- No new `_PUBLIC_ROUTES` entries (Init 6 default-deny preserved).
- No production-code changes outside `UsersPage.tsx` + backend `router.py list_admin_users` filter clause.
- No bulk operations (FR5-ADMIN-4 hard rule).
- No invites-tab work (Story 12.1 already shipped).
