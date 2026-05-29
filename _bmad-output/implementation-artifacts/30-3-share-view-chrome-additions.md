# Story 30.3: Frontend share-view chrome additions (Sign in + LangToggle + ThemeToggle)

Status: ready-for-dev

## Story

As a **recipient of a `/share/<token>` link**,
I want **the share-view header to expose Sign in, language, and theme controls without changing the anonymous content surface**,
so that **(B3/B4) absentee members can recognize the affordance and sign in if they have an account, and any recipient can adjust language/theme to their preference**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md` § §4.1 + §4.2 + §4.3 (Story 30.3 entry). Source UX rec: `_bmad-output/ux/share-flow-membership-path-ux.md` Deliverable 1 (Option a, right-aligned combined-with-banner) + Deliverable 2 not in scope here (Story 30.2) + Deliverable 3 (single-string "Zaloguj się" / "Sign in" copy). Memory carve-out: `[[feedback_share_view_scope_boundary]]` 2026-05-25 amendment permits CHROME-affordance additions on anonymous share view (NOT CONTENT enrichment). **Codex tag:** `gpt-5.4-mini` (routine FE composition + CSS, no security class — per [[feedback_codex_model_routing]]).

**Independent of Stories 30.1 and 30.2** — can land in parallel. Story 30.1's hardened `validateSearch` accepts `/share/<token>` paths produced by this story's SignInButton (RU-1 happy case already covers it).

## Acceptance Criteria

### AC-1 — Share-view header gains three right-aligned controls (mirrors TopBar order)

`apps/web/src/routes/share/$token.tsx` header (lines 480-485 today) becomes a two-side flex layout:

- **Left side:** existing `share.view.brand` text + existing `share.view.banner_anonymous` text (unchanged).
- **Right side:** `<ThemeToggle />` + `<LangToggle />` + `<SignInButton token={token} />` in that order — **identical** order to member `TopBar.tsx:16-18` so a recipient who later switches to member view sees consistent affordance placement.

### AC-2 — SignInButton navigates to `/login?next=/share/<token>`

`SignInButton` component handles click via `useNavigate()` → `navigate({ to: "/login", search: { next: \`/share/\${token}\` } })`. The frontend `LoginSearch.next` field already exists (Story 11.3) and Story 30.1's `_isSafeReturnPath` accepts `/share/<token>` (RU-1 verified). Post-login navigation to `next` is existing `login.tsx` behavior; no new login-side wiring needed.

### AC-3 — SignInButton visual spec (Sally Deliverable 1)

- Element: `<button type="button">` (NOT `<Link>` — `useNavigate` programmatic call lets us emit `replace: false` cleanly and keeps the button vs link semantics correct: this is an action, not a doc link).
- Tailwind classes (using existing CSS tokens, no inline hex):
  `inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring`
- Icon: `LogIn` from `lucide-react` (already in deps via existing UserMenu usage), `size-4` left of label.
- aria-label: from `t("share.view.signin_aria")` (slightly more descriptive than visible label — assistive-tech listeners get the action explained).
- Visible label: from `t("share.view.signin_cta")`.

### AC-4 — Two new i18n keys in BOTH en.json and pl.json

Exact key names + values (Polish diacritics correct per global i18n directive):

| Key | PL value | EN value |
|---|---|---|
| `share.view.signin_cta` | `Zaloguj się` | `Sign in` |
| `share.view.signin_aria` | `Zaloguj się, aby zobaczyć więcej opcji` | `Sign in to access more options` |

Pre-merge grep invariant: every new key present in BOTH locale files with non-empty value (G2 in T6).

### AC-5 — Responsive layout (mobile < 640px)

Per Sally Deliverable 1 mobile mockup:

- **Mobile (<640px):** the right-side control group wraps to a second row below the brand+banner row. Banner text MUST remain readable (no horizontal crop). Toggles + Sign in button stay grouped together; same order ThemeToggle → LangToggle → SignInButton.
- **Desktop (≥640px):** single row, controls right-aligned.

Implementation: existing header uses `flex items-center justify-between` on a `max-w-5xl` inner div. Add `flex-wrap gap-2` to allow controls to wrap below brand+banner on narrow viewports, OR use a responsive `flex-col sm:flex-row` shape. Spec author picks the cleaner shape based on actual viewport check (Playwright mobile baseline regen verifies AC-5 mechanically).

### AC-6 — Theme + Lang toggles function exactly as in member TopBar

The `<ThemeToggle />` and `<LangToggle />` components are reused as-is from `apps/web/src/shell/` — NO copy, NO fork, NO new variants. Story 30.3 imports them directly. They depend on `useTheme()` + `useTranslation()`/`i18n`, both of which are already provided by `__root.tsx` (`ThemeProvider` + `LangProvider`) above the route tree, so they work correctly inside the share route. Pre-merge grep invariant: only ONE `ThemeToggle.tsx` and ONE `LangToggle.tsx` file exist (G3 in T6).

### AC-7 — Anonymous share-view CONTENT is UNCHANGED

`[[feedback_share_view_scope_boundary]]` carve-out 2026-05-25 explicitly preserves the terminus on CONTENT: the carousel, STL list, 3D viewer, description block, footer notice MUST NOT change in Story 30.3. Only the header chrome receives additions.

Pre-merge invariant: `git diff apps/web/src/routes/share/$token.tsx` shows changes ONLY in the `<header>` block (lines 480-485 today) and possibly the imports at the top. The `AnonymousShareView` body (carousel + STL + description + footer) MUST stay byte-identical. T6 grep invariant G4 enforces this via diff line-count assertion on the body region.

### AC-8 — Visual baseline coverage × 4 projects (NEW spec)

NEW Playwright spec `apps/web/tests/visual/share-anonymous-with-signin.spec.ts` × 4 projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`) = **4 new PNG baselines** bundled in the SAME COMMIT per [[feedback_share_view_scope_boundary]] amended carve-out + FR13 Baseline Acceptance Gate (Story 5.13 husky hook enforces `baseline-reviewed:` sign-off in commit message).

The spec MUST:
- Override `/api/auth/me` → 401 (anonymous; per `api-stubs.ts` line 39 comment: "Specs that need anonymous behavior explicitly re-register /api/auth/me → 401"; Playwright matches handlers in reverse registration order so per-test override wins).
- Stub `/api/share/{token}` → 200 with a fixture `ShareModelView` payload (minimal: id + name_en + category + tags + thumbnail_url=null + has_3d=false + images=[] + notes_en + notes_pl=null + stl_url=null) to render the share view without 404.
- Stub `/api/share/{token}/files` → 200 with `{items: [], total: 0, page: 1, page_size: 50}` to satisfy the carousel fetch.
- Navigate to `/share/test-token-30-3`.
- Wait for the header to render (look for the SignInButton aria-label).
- `await expect(page).toHaveScreenshot("share-anonymous-with-signin.png")` per Playwright snapshot convention; framework automatically suffixes by project name (e.g., `share-anonymous-with-signin-desktop-light.png`).

### AC-9 — Vitest coverage (3 new tests)

Extend or create `apps/web/src/routes/share/$token.test.tsx` (or use existing test file). NEW `describe("Story 30.3 chrome additions", () => {...})` block:

- **CHROME-1**: render the share-view header → assert `<button>` with aria-label matching `Zaloguj się, aby zobaczyć więcej opcji` (Polish locale) is present.
- **CHROME-2**: click the Sign in button → assert the test router's location navigates to `/login` with `search.next === "/share/<token>"`.
- **CHROME-3**: assert both `<ThemeToggle />` and `<LangToggle />` are rendered in the header (DOM presence check — `getByRole("button", { name: /toggle theme|przełącz motyw/i })` and the LangToggle role=group with aria-label="Language").

### AC-10 — Color tokens only (project-context.md compliance)

NO inline hex colors anywhere in the new component or modified header. All visuals use Tailwind classes referencing CSS variables in `apps/web/src/styles/theme.css` (`bg-card`, `text-foreground`, `border-border`, `bg-muted`, `outline-ring`). Pre-merge grep invariant: `grep -nE "#[0-9a-fA-F]{3,6}\b" apps/web/src/routes/share/$token.tsx` and the new SignInButton file return ZERO hex hits (G5).

### AC-11 — react-refresh/only-export-components compliance

If the SignInButton component is colocated in a route file, the file MUST NOT export multiple non-component values to satisfy ESLint `react-refresh/only-export-components` warn-as-error rule. SignInButton goes in a SEPARATE file: `apps/web/src/routes/share/SignInButton.tsx` (or under `apps/web/src/ui/custom/SignInButton.tsx` — spec author picks per existing UI primitive placement convention). G6 grep invariant: `npm run lint -- --max-warnings=0` returns clean.

## Tasks / Subtasks

- [ ] **T1** (AC-2, AC-3, AC-10, AC-11) — Create `SignInButton` component
  - [ ] T1.1 New file `apps/web/src/routes/share/SignInButton.tsx` (colocated with `$token.tsx`; reuses TanStack Router param convention; no need to promote to `@/ui/custom/` since it's share-flow-specific). Imports: `useNavigate` from `@tanstack/react-router`, `useTranslation` from `react-i18next`, `LogIn` from `lucide-react`.
  - [ ] T1.2 Component signature: `export function SignInButton({ token }: { token: string })`. Render `<button type="button" onClick={...} aria-label={t("share.view.signin_aria")} className="...">` with `<LogIn className="size-4" />` + `{t("share.view.signin_cta")}` inside.
  - [ ] T1.3 onClick body: `void navigate({ to: "/login", search: { next: \`/share/\${token}\` }, replace: false })`.
  - [ ] T1.4 Tailwind classes verbatim per AC-3 visual spec. No inline hex.

- [ ] **T2** (AC-1, AC-5, AC-6, AC-7) — Modify share-view header in `apps/web/src/routes/share/$token.tsx`
  - [ ] T2.1 Add imports at top: `import { LangToggle } from "@/shell/LangToggle"; import { ThemeToggle } from "@/shell/ThemeToggle"; import { SignInButton } from "./SignInButton";` (alphabetized per ESLint import order).
  - [ ] T2.2 Replace the existing header block (line 480-485):
    ```tsx
    <header className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <span className="text-sm font-semibold text-foreground">{t("share.view.brand")}</span>
        <span className="text-xs text-muted-foreground">{t("share.view.banner_anonymous")}</span>
      </div>
    </header>
    ```
    with the new shape:
    ```tsx
    <header className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-foreground">{t("share.view.brand")}</span>
        <span className="flex-1 text-xs text-muted-foreground">
          {t("share.view.banner_anonymous")}
        </span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <LangToggle />
          <SignInButton token={token} />
        </div>
      </div>
    </header>
    ```
    `flex-wrap` lets the control group wrap below brand+banner on narrow viewports (AC-5); `flex-1` on the banner text claims remaining horizontal space on desktop so the control group hugs the right edge.
  - [ ] T2.3 Verify the `AnonymousShareView` function signature ALREADY receives `token` via `({ token }: { token: string })` (line 408) — no signature change needed; `token` flows through to `SignInButton` directly.
  - [ ] T2.4 NO changes to the `<main>` body (carousel, STL section, description, footer) — AC-7 invariant.

- [ ] **T3** (AC-4) — Append 2 new i18n keys to BOTH locale files
  - [ ] T3.1 `apps/web/src/locales/en.json` — add (alphabetized merge near existing `share.view.brand` and `share.view.banner_anonymous` at lines 499-500):
    ```json
      "share.view.signin_cta": "Sign in",
      "share.view.signin_aria": "Sign in to access more options",
    ```
  - [ ] T3.2 `apps/web/src/locales/pl.json` — same positions, Polish values:
    ```json
      "share.view.signin_cta": "Zaloguj się",
      "share.view.signin_aria": "Zaloguj się, aby zobaczyć więcej opcji",
    ```
  - [ ] T3.3 Verify trailing commas + JSON validity via `node -e "require('./apps/web/src/locales/pl.json'); require('./apps/web/src/locales/en.json'); console.log('valid');"` (or rely on tsc/vite to catch).

- [ ] **T4** (AC-9) — Vitest coverage (3 new tests CHROME-1/2/3)
  - [ ] T4.1 Locate existing `apps/web/src/routes/share/$token.test.tsx` (already exists per file listing) OR create new sibling test file `SignInButton.test.tsx`. Spec author picks: prefer extending `$token.test.tsx` if its test surface already exercises `AnonymousShareView`; otherwise sibling file for the SignInButton unit + separate integration in $token.test for header composition.
  - [ ] T4.2 **CHROME-1** (SignInButton presence + aria-label PL):
    ```tsx
    it("CHROME-1: renders Sign in button with Polish aria-label", () => {
      // assume i18n init sets PL; if not, force via i18n.changeLanguage("pl") in beforeEach
      render(<AnonymousShareView token="abc123" />);
      const btn = screen.getByRole("button", { name: /Zaloguj się, aby zobaczyć więcej opcji/i });
      expect(btn).toBeInTheDocument();
    });
    ```
  - [ ] T4.3 **CHROME-2** (SignInButton onClick navigates):
    ```tsx
    it("CHROME-2: navigates to /login?next=/share/<token> on click", async () => {
      const { router } = renderWithRouter(<AnonymousShareView token="abc123" />);
      const btn = screen.getByRole("button", { name: /Zaloguj się, aby zobaczyć więcej opcji/i });
      fireEvent.click(btn);
      await waitFor(() => {
        expect(router.state.location.pathname).toBe("/login");
        expect(router.state.location.search).toEqual({ next: "/share/abc123" });
      });
    });
    ```
    (`renderWithRouter` mirrors the pattern in `login.test.tsx:renderLoginWithNext` — create a minimal TanStack memory router with `/login` + `/share/$token` routes.)
  - [ ] T4.4 **CHROME-3** (ThemeToggle + LangToggle presence):
    ```tsx
    it("CHROME-3: renders ThemeToggle and LangToggle in header", () => {
      render(<AnonymousShareView token="abc123" />);
      expect(screen.getByRole("button", { name: /Przełącz motyw|toggle theme/i })).toBeInTheDocument();
      expect(screen.getByRole("group", { name: /language/i })).toBeInTheDocument();
    });
    ```
  - [ ] T4.5 Per [[feedback_vitest_manual_cleanup]] memory note: global `vitest.setup.ts` (commit a026e97) auto-registers `afterEach(cleanup)`, so test files no longer need the boilerplate. New `SignInButton.test.tsx` (if created) inherits this.

- [ ] **T5** (AC-8) — NEW Playwright visual spec
  - [ ] T5.1 Create `apps/web/tests/visual/share-anonymous-with-signin.spec.ts`:
    ```typescript
    import { test, expect } from "./_test";

    const TOKEN = "test-token-30-3";

    const SHARE_VIEW_FIXTURE = {
      id: "00000000-0000-0000-0000-000000000030",
      name_en: "Test Share Model",
      name_pl: "Testowy model udostępniony",
      category: "test",
      tags: ["sample"],
      thumbnail_url: null,
      has_3d: false,
      images: [],
      notes_en: "Sample share-view content for visual baseline.",
      notes_pl: "Przykładowa zawartość udostępniona dla baseline wizualnego.",
      stl_url: null,
      stl_size_bytes: null,
    };

    test.describe("Story 30.3 — share-view chrome additions", () => {
      test("anonymous share view with new chrome (Sign in + Theme + Lang)", async ({ page }) => {
        // Override /api/auth/me → 401 (anonymous; per api-stubs.ts the default
        // returns ADMIN — explicitly re-register; Playwright matches in
        // reverse registration order so per-test override wins).
        await page.route("**/api/auth/me", (route) =>
          route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"missing_access"}' }),
        );
        await page.route(`**/api/share/${TOKEN}`, (route) =>
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(SHARE_VIEW_FIXTURE),
          }),
        );
        await page.route(`**/api/share/${TOKEN}/files`, (route) =>
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }),
          }),
        );

        await page.goto(`/share/${TOKEN}`);
        // Wait for the SignInButton to be visible (aria-label is stable across locales).
        await page.getByRole("button", { name: /Zaloguj się|Sign in/i }).first().waitFor();

        await expect(page).toHaveScreenshot("share-anonymous-with-signin.png", {
          fullPage: false,
          animations: "disabled",
        });
      });
    });
    ```
  - [ ] T5.2 Run `npx playwright test --config=apps/web/tests/visual/playwright.config.ts --update-snapshots tests/visual/share-anonymous-with-signin.spec.ts` from `apps/web/` to generate the 4 new PNG baselines (× 4 projects = 4 snapshots; Playwright auto-suffixes by project).
  - [ ] T5.3 Stage all 4 PNGs in the same commit as the code change. Commit message MUST include `baseline-reviewed: share-anonymous-with-signin.png, Ezop, 2026-05-25` line PER PNG per FR13 Baseline Acceptance Gate (commit-msg husky hook enforces; missing sign-off rejects the commit with exit 1).

- [ ] **T6** (full quality gate) — Pre-merge invariants
  - [ ] T6.1 `cd /home/ezop/repos/3d-portal/apps/web && timeout 120 npm run test -- --run` returns green; new vitest count = baseline + 3 (CHROME-1/2/3).
  - [ ] T6.2 `cd /home/ezop/repos/3d-portal/apps/web && npm run lint && npx tsc --noEmit` returns clean (G6).
  - [ ] T6.3 `cd /home/ezop/repos/3d-portal/apps/web && timeout 300 npm run build` returns green (per [[feedback_pre_merge_gate_checklist]] — `tsc` alone misses code-split warnings; full build catches them).
  - [ ] T6.4 `cd /home/ezop/repos/3d-portal/apps/web && timeout 300 npx playwright test --config=tests/visual/playwright.config.ts tests/visual/share-anonymous-with-signin.spec.ts` (after T5.2 baseline regen) returns green × 4 projects.
  - [ ] T6.5 **Pre-merge grep checklist (6 invariants):**
    - [ ] G1: `grep -nE "<SignInButton|<ThemeToggle|<LangToggle" apps/web/src/routes/share/$token.tsx` returns 3+ hits (one per control).
    - [ ] G2: `grep -nE "share\.view\.signin_(cta|aria)" apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns 4+ hits (2 keys × 2 files).
    - [ ] G3: `find apps/web/src -name "ThemeToggle.tsx" -o -name "LangToggle.tsx" | wc -l` returns `2` (one each — no fork).
    - [ ] G4: AC-7 body-unchanged sanity — `git diff apps/web/src/routes/share/$token.tsx` shows new lines only in the import block + `<header>` block; no diff lines in `<main>`/carousel/STL/description/footer regions. Operator-verifiable; not a mechanical grep gate but called out for the spec author to manually confirm before commit.
    - [ ] G5: `grep -nE "#[0-9a-fA-F]{3,6}\b" apps/web/src/routes/share/$token.tsx apps/web/src/routes/share/SignInButton.tsx` returns ZERO hex hits.
    - [ ] G6: `npm run lint -- --max-warnings=0` returns clean (covers `react-refresh/only-export-components` per AC-11).

- [ ] **T7** (handoff to deploy + close-out)
  - [ ] T7.1 Story file Dev Agent Record gets file list (5 files expected: SignInButton.tsx NEW, $token.tsx MOD, en.json MOD, pl.json MOD, share-anonymous-with-signin.spec.ts NEW + 4 PNGs) + completion notes per template.
  - [ ] T7.2 Sprint-status flip `30-3-share-view-chrome-additions: ready-for-dev → in-progress → review → done` per BMAD convention (dev-story owns the `→ review` flip; codex-review-pass owns the `→ done` flip).
  - [ ] T7.3 Auto-deploy to `.190` per [[feedback_auto_deploy_dev]] (this is code change, not doc-only; full `deploy.sh` post-merge).
  - [ ] T7.4 Note in close-out commit message: chrome additions DO NOT change anonymous CONTENT (per [[feedback_share_view_scope_boundary]] amended carve-out). Phase B (anonymous CONTENT parity) remains deferred as future-initiative candidate.

## Dev Notes

### Source-of-truth references

- **PRD:** `_bmad-output/planning-artifacts/prd.md` § Initiative 18 — FR18-CHROME-ADDITIONS-1, FR18-RETURN-URL-1 (Sign in click navigation portion), NFR18-VISUAL-VERIFICATION-1, NFR18-I18N-PARITY-1.
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md` § Initiative 18 — no decision specifically owned by Story 30.3 (Decisions AA/AB/AC are owned by 30.1/30.2). Story 30.3 is pure FE composition.
- **SCP:** `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md` § §4.1 + §4.2 + §4.3 (Story 30.3 entry, including 6 pre-merge invariants).
- **UX rec:** `_bmad-output/ux/share-flow-membership-path-ux.md` Deliverable 1 (Sign in placement, Option a right-aligned combined-with-banner, locked 2026-05-25) + Deliverable 3 (single-string copy, locked 2026-05-25). Decision 2 approved adding Lang+Theme toggles alongside Sign in (operator 2026-05-25).
- **Brainstorm:** `_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md` § Phase 3 Cross-Pollination (Notion/GitHub "always-on login affordance" pattern justifies the chrome-level placement) + § Phase 4 implementation hot-spot `rα-3` ("Sign in" button needs sufficient visual weight).
- **Memory entries (mandatory):**
  - [[feedback_share_view_scope_boundary]] (amended 2026-05-25 with carve-out) — chrome affordances + Lang/Theme toggles ARE NOT share-view content enrichment; visual baseline regen is warranted (NOT operator-manual-verify), unlike anonymous content changes which would still require operator manual verify.
  - [[feedback_frontend_visual_verification]] — Stories 30.2 + 30.3 carry visual baseline regen × 4 projects per project-context.md mandate.
  - [[feedback_vitest_manual_cleanup]] — global vitest.setup.ts auto-registers afterEach(cleanup) since commit a026e97; new test files no longer need the boilerplate (T4.5 reference).
  - [[feedback_codex_model_routing]] — Story 30.3 routes to gpt-5.4-mini (routine FE composition + CSS, no security class).
  - [[feedback_pre_merge_gate_checklist]] — T6 pre-merge invariants list is the operational gate; `npm run build` (T6.3) catches code-split warnings that `tsc` alone misses.
  - [[feedback_lazy_import_discipline]] — Story 30.3 imports `<ThemeToggle />` and `<LangToggle />` directly from `@/shell/`; these are SMALL primitives, not heavy lazy() barrels — direct import is correct shape.
  - [[feedback_shared_cache_in_react]] — N/A for Story 30.3 (no module-level cache introduced).

### Pre-enumeration findings (saved scope cuts)

Per [[feedback_scp_pre_enumeration_phase]] enumeration phase 2026-05-25:

1. **`ThemeToggle.tsx` and `LangToggle.tsx` ALREADY EXIST** at `apps/web/src/shell/` (Init 0 / Init 3 era). Both are stable, generic, and have no per-route assumptions — Story 30.3 imports them as-is. **Scope cut:** no new toggle components.
2. **`useNavigate` from `@tanstack/react-router`** is the established pattern (used in `login.tsx`, `__root.tsx`, `AppShell.tsx`, `AuthGate.tsx`). **Scope cut:** no new navigation primitive.
3. **`LogIn` icon from `lucide-react`** is already a project dep (declared in `package.json` via the `lucide-react` package; used in `Settings2faPage.tsx` and elsewhere). **Scope cut:** no new dependency.
4. **`useTheme` from `@/shell/ThemeProvider`** is provided by `__root.tsx` for the entire route tree — the share route already has access (visible by the fact that anonymous-share view today doesn't crash on render). **Scope cut:** no provider plumbing.
5. **`/login?next=...` query convention** is established (Story 11.3 + Story 30.1 hardening). **Scope cut:** no new login-side wiring.
6. **`api-stubs.ts` test fixture infrastructure** (Playwright visual harness) already supports per-test handler overrides. **Scope cut:** no new fixture infrastructure.

Net scope after enumeration: **1 NEW file (SignInButton.tsx) + 1 NEW visual spec + 3 MODIFIED files ($token.tsx + en.json + pl.json) + 4 NEW visual baseline PNGs + optionally 1 NEW or MODIFIED vitest file**. Small footprint, all routine FE composition.

### Files this story touches

| File | Action | Why |
|---|---|---|
| `apps/web/src/routes/share/SignInButton.tsx` | CREATE | T1 — new component |
| `apps/web/src/routes/share/$token.tsx` | MODIFY (header only, body untouched) | T2 — header gets 3 right-side controls |
| `apps/web/src/locales/en.json` | MODIFY (2 new keys) | T3.1 |
| `apps/web/src/locales/pl.json` | MODIFY (2 new keys) | T3.2 |
| `apps/web/src/routes/share/$token.test.tsx` OR `apps/web/src/routes/share/SignInButton.test.tsx` | EXTEND or CREATE (3 new tests) | T4 — vitest CHROME-1/2/3 |
| `apps/web/tests/visual/share-anonymous-with-signin.spec.ts` | CREATE | T5.1 — new visual spec |
| `apps/web/tests/visual/__snapshots__/share-anonymous-with-signin.spec.ts/share-anonymous-with-signin-{desktop-light,desktop-dark,mobile-light,mobile-dark}.png` | CREATE (4 PNGs) | T5.2 — visual baselines bundled in same commit per FR13 |

**Files this story MUST NOT touch:**

- `apps/web/src/shell/ThemeToggle.tsx`, `apps/web/src/shell/LangToggle.tsx`, `apps/web/src/shell/TopBar.tsx` — reused as-is, no fork.
- `apps/web/src/routes/login.tsx` — Story 30.1 already hardened `validateSearch`; CTAs that use `?next=/share/<token>` already work via the existing `LoginSearch.next` field.
- `apps/api/app/modules/share/*` — backend Story 30.1 owns those; chrome additions are pure FE.
- `AnonymousShareView` body (carousel, STL, description, footer) — AC-7 invariant per [[feedback_share_view_scope_boundary]] terminus.
- Any module under `apps/web/src/modules/catalog/` — no catalog component reuse in Story 30.3 (that's Story 30.2's MemberShareView surface).

### Implementation skeleton

**`apps/web/src/routes/share/SignInButton.tsx`** (NEW):

```tsx
import { useNavigate } from "@tanstack/react-router";
import { LogIn } from "lucide-react";
import { useTranslation } from "react-i18next";

// Initiative 18 Story 30.3 / FR18-CHROME-ADDITIONS-1 — Sign in affordance
// rendered in the anonymous share-view header. Navigates to /login carrying
// the original /share/<token> as `next` so post-login lands the recipient
// back on the share link they came from. Story 30.1 hardened
// `validateSearch` accepts this path shape (RU-1 happy case).
export function SignInButton({ token }: { token: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() =>
        void navigate({
          to: "/login",
          search: { next: `/share/${token}` },
          replace: false,
        })
      }
      aria-label={t("share.view.signin_aria")}
      className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      <LogIn className="size-4" />
      {t("share.view.signin_cta")}
    </button>
  );
}
```

**`apps/web/src/routes/share/$token.tsx`** (header block replacement, line 480-485):

Diff sketch:

```diff
+import { LangToggle } from "@/shell/LangToggle";
+import { ThemeToggle } from "@/shell/ThemeToggle";
+import { SignInButton } from "./SignInButton";

 ...

-      <header className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
-        <div className="mx-auto flex max-w-5xl items-center justify-between">
-          <span className="text-sm font-semibold text-foreground">{t("share.view.brand")}</span>
-          <span className="text-xs text-muted-foreground">{t("share.view.banner_anonymous")}</span>
-        </div>
-      </header>
+      <header className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
+        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2">
+          <span className="text-sm font-semibold text-foreground">{t("share.view.brand")}</span>
+          <span className="flex-1 text-xs text-muted-foreground">
+            {t("share.view.banner_anonymous")}
+          </span>
+          <div className="flex items-center gap-2">
+            <ThemeToggle />
+            <LangToggle />
+            <SignInButton token={token} />
+          </div>
+        </div>
+      </header>
```

**`apps/web/src/locales/en.json`** (insertion near existing `share.view.brand` line 499):

```diff
   "share.view.brand": "3D Portal",
   "share.view.banner_anonymous": "You're viewing a shared model",
+  "share.view.signin_cta": "Sign in",
+  "share.view.signin_aria": "Sign in to access more options",
```

**`apps/web/src/locales/pl.json`** (same position, PL values):

```diff
   "share.view.brand": "Portal 3D",
   "share.view.banner_anonymous": "Oglądasz udostępniony model",
+  "share.view.signin_cta": "Zaloguj się",
+  "share.view.signin_aria": "Zaloguj się, aby zobaczyć więcej opcji",
```

### Conventions to follow (recap from project-context.md)

- **i18n is mandatory for user-visible strings.** Both en+pl get the new keys (T3) per i18n parity rule. Polish diacritics enforced (memory directive).
- **No inline hex colors** (T1.4 + AC-10 + G5). Use CSS-token Tailwind classes only.
- **Path alias `@/*`** for cross-module imports (T2.1 — `@/shell/LangToggle` etc.). No deep relative chains across module boundaries.
- **ESLint flat config + `--max-warnings=0`** (T6.2 + G6). `react-refresh/only-export-components` warn-as-error — keep SignInButton as the sole component export of its file (AC-11).
- **Visual regression mandatory for any UI change** — T5 + AC-8 + 4 baselines × 4 projects (NFR18-VISUAL-VERIFICATION-1). FR13 Baseline Acceptance Gate enforces commit-message sign-off via husky hook.
- **Per [[feedback_share_view_scope_boundary]] amended carve-out 2026-05-25:** visual baseline regen for membership-path CHROME is warranted (Story 30.3 establishes the FIRST visual baseline for the anonymous share view per the carve-out); CONTENT changes would still require operator manual verify (Phase B deferred).
- **Conventional commits with `share` scope** (per project-context.md scope list) — e.g., `feat(share): chrome additions (Sign in + Lang + Theme toggles) on anonymous view (Story 30.3, Init 18)`.

### Project Structure Notes

- `SignInButton.tsx` colocated next to `$token.tsx` under `apps/web/src/routes/share/` — share-flow-specific, single-purpose, not a project-wide UI primitive. Promoting to `@/ui/custom/` is unnecessary unless a second route ever needs it (YAGNI).
- Visual spec under `apps/web/tests/visual/` (project standard).
- No deviation from project structure; no new directories.

### References

- [Source: `apps/web/src/routes/share/$token.tsx:408`] — `AnonymousShareView({ token }: { token: string })` signature confirms `token` is in scope for the SignInButton prop without further plumbing.
- [Source: `apps/web/src/routes/share/$token.tsx:480-485`] — current header block (T2 modification target).
- [Source: `apps/web/src/shell/TopBar.tsx:16-18`] — control order to mirror: `<ThemeToggle /> <LangToggle /> <UserMenu/SignInButton/>`.
- [Source: `apps/web/src/shell/ThemeToggle.tsx`] — component shape (size-icon Button + Sun/Moon toggle + `t("common.theme.toggle")` aria).
- [Source: `apps/web/src/shell/LangToggle.tsx`] — component shape (role="group" wrapping two PL/EN buttons; aria-label="Language" hardcoded).
- [Source: `apps/web/src/routes/login.tsx`] — `LoginSearch.next` field + `_isSafeReturnPath` Story 30.1 hardening accepting `/share/<token>` paths (RU-1 verified).
- [Source: `apps/web/src/locales/en.json:499-500` + `pl.json:499-500`] — existing `share.view.brand` + `share.view.banner_anonymous` keys (T3 insertion target).
- [Source: `apps/web/tests/visual/_test.ts`] — Playwright fixture default `/api/auth/me` → 200 admin; T5.1 overrides to 401 for anonymous.
- [Source: `apps/web/tests/visual/api-stubs.ts:39`] — comment explaining the per-test override pattern (Playwright matches handlers in reverse registration order).
- [Source: Existing `apps/web/src/routes/login.test.tsx:237-313`] — `renderLoginWithNext` test helper pattern (T4 inspiration for `renderWithRouter`).
- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 18] — no Story 30.3-specific decision; chrome composition is straightforward.
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 18 FR18-CHROME-ADDITIONS-1 + FR18-RETURN-URL-1] — functional requirements covered by Story 30.3.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) via bmad-dev-story skill

### Debug Log References

(populated by dev-story execution)

### Completion Notes List

(populated by dev-story execution)

### File List

(populated by dev-story execution — expected: 5 files + 4 PNGs)

- apps/web/src/routes/share/SignInButton.tsx (NEW)
- apps/web/src/routes/share/$token.tsx (MOD: imports + header block)
- apps/web/src/locales/en.json (MOD: +2 keys)
- apps/web/src/locales/pl.json (MOD: +2 keys)
- apps/web/src/routes/share/$token.test.tsx OR SignInButton.test.tsx (EXTEND or CREATE: +3 tests)
- apps/web/tests/visual/share-anonymous-with-signin.spec.ts (NEW)
- apps/web/tests/visual/__snapshots__/share-anonymous-with-signin.spec.ts/share-anonymous-with-signin-*.png (NEW × 4)
