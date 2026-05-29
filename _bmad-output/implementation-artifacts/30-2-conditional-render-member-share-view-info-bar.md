# Story 30.2: Frontend conditional render + MemberShareView + dismissible info-bar

Status: ready-for-dev

## Story

As an **active member receiving a `/share/<token>` link from another member (recipient state B5)**,
I want **to see the canonical catalog detail UI at the share URL instead of the minimal anonymous view**,
so that **I get full member-experience parity (TopBar, ModuleRail, gallery, comments) without losing the share URL for bookmarking, and I see a dismissible info-bar pointing me at the canonical `/catalog/$id` URL**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md` § §4.1-§4.3 (Story 30.2 entry). Architectural anchors: Decision AB (`architecture.md` § Initiative 18 — conditional AppShell bypass on `/share/*`) + Decision AC (info-bar sessionStorage dismissal). UX rec: `_bmad-output/ux/share-flow-membership-path-ux.md` Deliverable 2 (Variant γ — full canonical member view + dismissible info-bar). **Codex tag:** `gpt-5.4-mini` (routine FE composition + new component, no security class).

**Depends on:** Story 30.1 SHIPPED (commit `cdb6fc1`, endpoint `GET /api/me/share-links/<token>/resolve` live on `.190`). Independent of Story 30.3 (chrome additions on the anonymous render).

## Acceptance Criteria

### AC-1 — `/share/<token>` route splits on `useAuth()` result

`apps/web/src/routes/share/$token.tsx` `ShareTokenRoute` component (currently line 571) wraps the existing render with a `useAuth()`-gated branch:

- `auth.isAuthenticated === true` → render `<MemberShareView token={token} />`
- otherwise → render existing `<AnonymousShareView token={token} />` (current behavior + Story 30.3 chrome additions)

### AC-2 — `MemberShareView` calls resolve endpoint via `useShareResolve` hook

New `MemberShareView` component:

- Calls new `useShareResolve(token)` hook (new file `apps/web/src/routes/share/useShareResolve.ts`).
- Hook wraps `api<ShareResolveResponse>("/me/share-links/<token>/resolve")` in a `useQuery` with query-key `["share", "resolve", token]`.
- `retry: false` (404/401 are decisive — not transient).
- `staleTime: 5 * 60 * 1000` (5 min — matches AuthContext meQuery staleTime).
- Returns `{ data, isLoading, isError, error }`.

### AC-3 — `MemberShareView` render branches

- **isLoading** → `<LoadingState variant="skeleton-detail" />` (re-use existing from `@/ui/custom/LoadingState`).
- **isError + 404 (token invalid/expired/revoked/soft-deleted-model)** → fall through to `<AnonymousShareView token={token} />`. This is graceful degradation: a member visiting an expired share link sees the same "share link expired" error message as an anonymous visitor (existing share-view error path at `$token.tsx:445`).
- **isError + 401 (defensive, should not happen — caller is authenticated)** → also fall through to `<AnonymousShareView token={token} />`. Optionally `Sentry.captureMessage("share_resolve_401_for_authenticated_caller", ...)` for observability; out of scope if Sentry instrumentation balloons.
- **isError + other (5xx, network)** → existing `<EmptyState messageKey="errors.network" />` (reuse from `@/ui/custom/EmptyState`).
- **Success** → renders `<CatalogDetailBody id={data.model_id} />` + `<ShareMemberContextInfoBar modelId={data.model_id} />` (info-bar at top of main content area).

### AC-4 — `CatalogDetailBody` extracted from `CatalogDetail` for reuse

Existing `apps/web/src/modules/catalog/routes/CatalogDetail.tsx` (53 LOC) is refactored:

- Body extracted into NEW exported component `CatalogDetailBody({ id }: { id: string })` in the same file (or in a sibling file `CatalogDetailBody.tsx`; spec author picks).
- `CatalogDetail` becomes the route-bound wrapper:
  ```tsx
  export function CatalogDetail() {
    const { id } = useParams({ from: "/catalog/$id" });
    return <CatalogDetailBody id={id} />;
  }
  ```
- ZERO behavior change for the canonical `/catalog/$id` route — pure refactor extracted for reuse.
- Pre-merge invariant G1: existing catalog detail visual baselines (`apps/web/tests/visual/catalog-detail.spec.ts/*`) stay byte-identical (no snapshot regen).

### AC-5 — `ShareMemberContextInfoBar` with sessionStorage dismissal (Decision AC)

NEW component `apps/web/src/routes/share/ShareMemberContextInfoBar.tsx`:

- **Props:** `modelId: string`.
- **Layout:** shadcn `Alert` primitive OR a hand-rolled component (`Alert` is the cleanest match — info variant). Tailwind: `mb-4 flex items-center justify-between gap-3 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm`.
- **Content:**
  - Left: `<Info className="size-4 shrink-0 text-muted-foreground" />` + `t("share.member_context.banner")`.
  - Right: `<Link to="/catalog/$id" params={{ id: modelId }}>{t("share.member_context.open_in_catalog")}</Link>` + `<button onClick={dismiss} aria-label={t("share.member_context.dismiss_aria")}><X className="size-4" /></button>`.
- **Dismissal state:** `sessionStorage.getItem("share-context-dismissed:" + modelId)` on mount; if present, render null. Click dismiss → `sessionStorage.setItem("share-context-dismissed:" + modelId, "1")` + `setDismissed(true)`.
- **sessionStorage unavailable edge case** (private browsing strict mode, embedded WebView): wrap reads/writes in try/catch; on failure, fall back to in-memory dismissal for the component lifetime (always re-renders on mount). Per Decision AC: "fail-open, never silently swallows the affordance".

### AC-6 — AppShell.tsx conditional bypass (Decision AB)

`apps/web/src/shell/AppShell.tsx` line 60 `if (isSharePath) return <>{children}</>;` becomes conditional:

```tsx
const shouldBypassForShare = isSharePath && !auth.isAuthenticated;
if (shouldBypassForShare) {
  return <>{children}</>;
}
```

Anonymous + auth-loading → bypass (existing behavior preserved). Authenticated → falls through to render the full AppShell (TopBar + ModuleRail + Outlet wrapping `MemberShareView`).

### AC-7 — AuthContext.tsx loosens `/auth/me` gating on `/share/*` (Init 18 Decision AB carve-out from Init 10 NFR10-SHARE-SECURITY-1)

**CRITICAL DESIGN DECISION** — pre-enumeration finding 2026-05-25:

`apps/web/src/shell/AuthContext.tsx:82-122` currently DISABLES the `/auth/me` query on `/share/*` routes via `enabled: !isAnonymousShareRoute` (line 102) — Init 10 Story 16.3 NFR10-SHARE-SECURITY-1 implemented this to make share view anonymous-by-design even for logged-in users. Init 18 Decision AB EXPLICITLY REVERSES THIS for `/share/*` so `useAuth()` can return real auth state and drive the conditional render (AC-1).

Story 30.2 modifies AuthContext.tsx:

- Remove the `isAnonymousShareRoute` short-circuit at line 109 (`if (isAnonymousShareRoute) return ANONYMOUS;`).
- Remove the `enabled: !isAnonymousShareRoute` gate at line 102 (always-enabled `meQuery`).
- Remove the `useReactivePathname` hook + `useEffect` that invalidates auth cache on share-route entry (lines 49-95) — no longer needed once the gating goes away. Keep the `window.history.pushState` monkey-patch ONLY if other callers depend on the `portal:locationchange` event (grep first; if no consumers, delete the monkey-patch too).
- Add an explicit comment block referencing Init 18 Decision AB carve-out:
  ```ts
  // Initiative 18 Story 30.2 (Decision AB) — Init 10 Story 16.3 originally
  // disabled the /auth/me query on /share/* routes to preserve an
  // anonymous-by-design property even for logged-in users (the share view
  // would render identical chrome regardless of session). Init 18 Decision AB
  // REVERSES this carve-out so /share/<token> can render the canonical
  // member experience (MemberShareView) for B5 callers. The NFR10
  // credentialless contract on /api/share/<token>/* (the data endpoints)
  // stays intact — fetchShareView() in @/lib/share-api still uses
  // `credentials: "omit"` for those endpoints. Only /auth/me carries
  // cookies, which is correct: it's not a /api/share/ endpoint.
  ```

**Why NOT a narrower carve-out (e.g., second `enabled` flag)**: simplicity. The original Init 10 gating was conservative defense-in-depth (the actual data-fetch contract is enforced by `fetchShareView`'s explicit `credentials: "omit"`, not by withholding `/auth/me`). Removing the gating restores normal auth behavior on `/share/*`; the NFR10 anonymous-data contract is not affected because `/api/auth/me` is NOT under `/api/share/`.

**Pre-merge invariant G2:** `grep -nE "fetchShareView|credentials:.*omit" apps/web/src/lib/share-api.ts` returns the existing pattern unchanged — the data-fetch credentialless contract MUST stay intact.

### AC-8 — Three new i18n keys in BOTH en.json and pl.json (Story 30.2 owns these)

| Key | PL value | EN value |
|---|---|---|
| `share.member_context.banner` | `Otworzyłeś ten model z linku udostępnionego.` | `You opened this model from a shared link.` |
| `share.member_context.open_in_catalog` | `Otwórz w katalogu` | `Open in catalog` |
| `share.member_context.dismiss_aria` | `Zamknij informację` | `Dismiss notice` |

Pre-merge grep invariant G3: every new key present in BOTH locale files with non-empty value.

### AC-9 — URL stays `/share/<token>` (no redirect)

`MemberShareView` MUST NOT call `navigate({ to: "/catalog/$id" })` on success. URL stability is the brainstorm rα-1 mitigation: recipient who clicked the share link from a chat app expects "back" to return to the chat, not bounce to a different URL. The info-bar's `<Link>` is the EXPLICIT affordance to switch to canonical URL if the recipient wants it.

Pre-merge invariant G4: `grep -nE "navigate\(.*catalog" apps/web/src/routes/share/MemberShareView.tsx` returns ZERO hits.

### AC-10 — Vitest coverage (6 new tests)

NEW or extended test file `apps/web/src/routes/share/MemberShareView.test.tsx` (or split across `MemberShareView.test.tsx` + `ShareMemberContextInfoBar.test.tsx`):

- **CR-1**: anonymous user (useAuth returns ANONYMOUS) on `/share/<token>` → `AnonymousShareView` rendered (regression guard for AC-1).
- **CR-2**: authenticated user on `/share/<token>` → `MemberShareView` rendered (calls resolve endpoint, then renders catalog body + info-bar).
- **IB-1**: `<ShareMemberContextInfoBar modelId="m1" />` on first mount → renders the banner text + action link + dismiss button.
- **IB-2**: click dismiss button → component re-renders null; assert info-bar text not in DOM.
- **IB-3**: re-mount `<ShareMemberContextInfoBar modelId="m2" />` after dismissing m1 → m2 info-bar STILL renders (different modelId scope).
- **IB-4**: pre-seed `sessionStorage.setItem("share-context-dismissed:m1", "1")` then mount `<ShareMemberContextInfoBar modelId="m1" />` → renders null on mount (no banner shown).

### AC-11 — Visual baseline coverage × 4 projects (2 NEW specs, 8 PNGs total)

NEW Playwright spec `apps/web/tests/visual/share-member-enriched.spec.ts` × 4 projects = 4 PNGs (B5 enrich-in-place with info-bar visible).
NEW Playwright spec `apps/web/tests/visual/share-member-enriched-dismissed.spec.ts` × 4 projects = 4 PNGs (B5 enrich-in-place after sessionStorage pre-seed dismisses the info-bar).

Both bundled in SAME COMMIT per FR13 Baseline Acceptance Gate. Each spec:

- Override `/api/auth/me` → 200 with member user (override default admin to make the test deterministic — covers the B5 case explicitly).
- Stub `/api/me/share-links/<TOKEN>/resolve` → 200 `{model_id: "<uuid>", access: "granted"}`.
- Stub `/api/models/<model_id>` → 200 with a minimal `ModelDetail` fixture (id + slug + name_en + category + files=[] + external_links=[] + minimal metadata to satisfy CatalogDetailBody render).
- Stub `/api/categories` etc. for ModelHero deps as needed (look at existing `catalog-detail.spec.ts` for the full stub set — reuse where possible).
- For the dismissed variant: `await page.addInitScript(() => sessionStorage.setItem("share-context-dismissed:<model_id>", "1"))` BEFORE `page.goto(...)`.
- Navigate to `/share/<TOKEN>`, wait for the catalog-detail body to render (`waitFor` ModelHero title), then snapshot.

### AC-12 — `useAuth()` returns real auth state on `/share/*` (verifies AC-7)

Direct unit test or implicit via CR-1/CR-2 in AC-10 — `useAuth()` MUST return authenticated state for logged-in users visiting `/share/<token>`. This is the smoking-gun assertion that AC-7's AuthContext loosening landed. Pre-merge grep invariant G5: `grep -nE "isAnonymousShareRoute|!isAnonymousShareRoute" apps/web/src/shell/AuthContext.tsx` returns ZERO hits (the gate was fully removed).

## Tasks / Subtasks

- [ ] **T1** (AC-7, AC-12) — Loosen AuthContext.tsx `/auth/me` gating on `/share/*`
  - [ ] T1.1 Read existing `apps/web/src/shell/AuthContext.tsx` fully (already done in pre-enumeration; confirm state hasn't changed since).
  - [ ] T1.2 Grep for consumers of `portal:locationchange` event: `grep -rnE "portal:locationchange|getAuthSnapshot" apps/web/src/` — if `getAuthSnapshot` and the event listener have no other consumers beyond AuthContext itself, the `useReactivePathname` hook + the `window.history` monkey-patch can also be removed; if they DO have consumers (e.g., `instrument-router.ts` consumes `getAuthSnapshot`), KEEP the monkey-patch + event emission but drop the `useReactivePathname` usage inside AuthProvider since the gating is gone.
  - [ ] T1.3 Edit AuthContext: remove `isAnonymousShareRoute` short-circuit (line 109), remove `enabled: !isAnonymousShareRoute` (line 102), remove the `useEffect` at lines 91-95 that invalidates auth cache on share-route entry (no longer needed), remove `useReactivePathname` invocation in AuthProvider body. The provider should now always run the `/auth/me` query and return real auth state regardless of route.
  - [ ] T1.4 Add the Init 18 Decision AB carve-out comment block (per AC-7 verbatim).
  - [ ] T1.5 Verify existing AuthContext tests still pass: `cd apps/web && npm run test -- --run src/shell/AuthContext.test.tsx`. If they assert on the share-route ANONYMOUS short-circuit, those assertions are now stale — update them to reflect the new behavior (authenticated user on `/share/*` returns real auth state) and document the Init 18 Decision AB carve-out in the test description.

- [ ] **T2** (AC-6) — AppShell.tsx conditional bypass
  - [ ] T2.1 Read existing `apps/web/src/shell/AppShell.tsx` line 25-62.
  - [ ] T2.2 Replace `if (isSharePath) return <>{children}</>;` (line 60) with:
    ```tsx
    // Initiative 18 Story 30.2 (Decision AB) — bypass share-path chrome ONLY
    // when the caller is anonymous. Authenticated callers on /share/<token>
    // get the full AppShell (TopBar + ModuleRail) so MemberShareView can
    // render the canonical member experience at the share URL (Variant γ
    // enrich-in-place). Anonymous render continues to use the route-local
    // header rendered by $token.tsx itself.
    const shouldBypassForShare = isSharePath && !auth.isAuthenticated;
    if (shouldBypassForShare) {
      return <>{children}</>;
    }
    ```
  - [ ] T2.3 The `useEffect` at lines 45-57 redirects unauthenticated visitors to `/login` for non-public, non-share paths. Confirm this STILL skips `/share/*` (existing `if (isSharePath || isPublicPath) return;` at line 47) — Story 30.2 does NOT change anonymous share-visit behavior; anonymous users on `/share/*` continue to see the share view without being redirected to login.

- [ ] **T3** (AC-4) — Refactor CatalogDetail to expose `CatalogDetailBody`
  - [ ] T3.1 Edit `apps/web/src/modules/catalog/routes/CatalogDetail.tsx`:
    ```tsx
    import { useParams } from "@tanstack/react-router";
    // ...existing imports...

    export function CatalogDetailBody({ id }: { id: string }) {
      const { data: detail, isLoading, isError, refetch } = useModel(id);
      // ...existing body verbatim, returning the <article>...</article> JSX...
    }

    export function CatalogDetail() {
      const { id } = useParams({ from: "/catalog/$id" });
      return <CatalogDetailBody id={id} />;
    }
    ```
  - [ ] T3.2 Verify ZERO behavior change for `/catalog/$id` — existing vitest + visual baselines for catalog-detail stay green WITHOUT snapshot regen.
  - [ ] T3.3 Pre-merge invariant G1: `apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/*` files are NOT regenerated (`git status` confirms no PNG diffs for those after running visual suite).

- [ ] **T4** (AC-2, AC-3) — New `useShareResolve` hook
  - [ ] T4.1 Create `apps/web/src/routes/share/useShareResolve.ts`:
    ```ts
    import { useQuery } from "@tanstack/react-query";
    import { api } from "@/lib/api";

    export interface ShareResolveResponse {
      model_id: string;
      access: "granted";
    }

    export function useShareResolve(token: string) {
      return useQuery<ShareResolveResponse>({
        queryKey: ["share", "resolve", token],
        queryFn: () => api<ShareResolveResponse>(`/me/share-links/${encodeURIComponent(token)}/resolve`),
        retry: false,
        staleTime: 5 * 60 * 1000,
      });
    }
    ```
  - [ ] T4.2 Hook MUST go through the standard `api()` wrapper (NOT raw `fetch`) so cookies + CSRF + 401-retry work correctly. The endpoint requires authentication per Story 30.1 AC-1.

- [ ] **T5** (AC-2, AC-3, AC-9) — New `MemberShareView` component
  - [ ] T5.1 Create `apps/web/src/routes/share/MemberShareView.tsx`:
    ```tsx
    import { ApiError } from "@/lib/api";
    import { CatalogDetailBody } from "@/modules/catalog/routes/CatalogDetail";
    import { EmptyState } from "@/ui/custom/EmptyState";
    import { LoadingState } from "@/ui/custom/LoadingState";

    import { AnonymousShareView } from "./$token";  // OR move AnonymousShareView to its own file first
    import { ShareMemberContextInfoBar } from "./ShareMemberContextInfoBar";
    import { useShareResolve } from "./useShareResolve";

    export function MemberShareView({ token }: { token: string }) {
      const { data, isLoading, isError, error, refetch } = useShareResolve(token);

      if (isLoading) {
        return <LoadingState variant="skeleton-detail" />;
      }

      if (isError) {
        const status = error instanceof ApiError ? error.status : 0;
        if (status === 404 || status === 401) {
          // Token invalid/expired/revoked/soft-deleted OR defensive
          // fallback for the (shouldn't-happen) authenticated-but-401 case.
          // Fall through to the anonymous view's existing token-invalid copy.
          return <AnonymousShareView token={token} />;
        }
        return (
          <EmptyState
            messageKey="errors.network"
            tone="error"
            action={{ labelKey: "common.retry", onClick: () => void refetch() }}
          />
        );
      }

      if (data === undefined) {
        // Defensive — should not reach (covered by isLoading + isError above).
        return <LoadingState variant="skeleton-detail" />;
      }

      return (
        <div className="space-y-4 px-4 pt-4">
          <ShareMemberContextInfoBar modelId={data.model_id} />
          <CatalogDetailBody id={data.model_id} />
        </div>
      );
    }
    ```
  - [ ] T5.2 Decide colocation of `AnonymousShareView`: today it's an inner function inside `$token.tsx`. Either (a) export it from `$token.tsx` for import, OR (b) extract to `apps/web/src/routes/share/AnonymousShareView.tsx` for cleaner separation. Spec author picks; option (b) is cleaner but is a larger refactor. Both work.

- [ ] **T6** (AC-5, AC-8) — New `ShareMemberContextInfoBar` component + 3 i18n keys
  - [ ] T6.1 Create `apps/web/src/routes/share/ShareMemberContextInfoBar.tsx`:
    ```tsx
    import { Link } from "@tanstack/react-router";
    import { Info, X } from "lucide-react";
    import { useEffect, useState } from "react";
    import { useTranslation } from "react-i18next";

    const KEY_PREFIX = "share-context-dismissed:";

    function _readDismissed(modelId: string): boolean {
      try {
        return typeof window !== "undefined" && window.sessionStorage.getItem(KEY_PREFIX + modelId) !== null;
      } catch {
        // sessionStorage unavailable (private browsing strict mode, embedded
        // WebView). Per Decision AC fail-open — always render the affordance.
        return false;
      }
    }

    function _writeDismissed(modelId: string): void {
      try {
        if (typeof window !== "undefined") {
          window.sessionStorage.setItem(KEY_PREFIX + modelId, "1");
        }
      } catch {
        // Same fallback: in-memory dismiss for component lifetime is enough.
      }
    }

    export function ShareMemberContextInfoBar({ modelId }: { modelId: string }) {
      const { t } = useTranslation();
      const [dismissed, setDismissed] = useState<boolean>(() => _readDismissed(modelId));

      // Re-check dismissed state when modelId changes (different share token
      // for a different model in the same session).
      useEffect(() => {
        setDismissed(_readDismissed(modelId));
      }, [modelId]);

      if (dismissed) return null;

      const handleDismiss = () => {
        _writeDismissed(modelId);
        setDismissed(true);
      };

      return (
        <div
          role="status"
          className="mb-4 flex items-center justify-between gap-3 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm"
        >
          <div className="flex items-center gap-2">
            <Info className="size-4 shrink-0 text-muted-foreground" />
            <span>{t("share.member_context.banner")}</span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/catalog/$id"
              params={{ id: modelId }}
              className="text-sm font-medium underline-offset-4 hover:underline"
            >
              {t("share.member_context.open_in_catalog")}
            </Link>
            <button
              type="button"
              onClick={handleDismiss}
              aria-label={t("share.member_context.dismiss_aria")}
              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      );
    }
    ```
  - [ ] T6.2 Add 3 i18n keys to `apps/web/src/locales/en.json` (alphabetized near `share.member_context.*`; place after `share.dialog.*` block):
    ```json
      "share.member_context.banner": "You opened this model from a shared link.",
      "share.member_context.open_in_catalog": "Open in catalog",
      "share.member_context.dismiss_aria": "Dismiss notice",
    ```
  - [ ] T6.3 Add 3 i18n keys to `apps/web/src/locales/pl.json` (same position, Polish values per AC-8):
    ```json
      "share.member_context.banner": "Otworzyłeś ten model z linku udostępnionego.",
      "share.member_context.open_in_catalog": "Otwórz w katalogu",
      "share.member_context.dismiss_aria": "Zamknij informację",
    ```

- [ ] **T7** (AC-1) — Modify `$token.tsx` `ShareTokenRoute` to split on `useAuth()`
  - [ ] T7.1 Read existing `$token.tsx` around line 571 (`ShareTokenRoute`).
  - [ ] T7.2 Modify `ShareTokenRoute`:
    ```tsx
    import { useAuth } from "@/shell/AuthContext";
    import { MemberShareView } from "./MemberShareView";

    function ShareTokenRoute() {
      const { token } = Route.useParams();
      const auth = useAuth();

      // Existing module-mount cleanup useEffect for shareBlobCache stays put
      // — it applies to both branches (anonymous + member). The blob cache
      // is keyed by URL; the member branch may not use AnonymousImage at
      // all, but the cleanup is benign in that case (empty maps to revoke).

      // Loading state: render a tiny placeholder rather than picking a
      // branch prematurely. Without this, the anonymous render would flash
      // first then swap to member view when /auth/me resolves.
      if (auth.isLoading) {
        return <LoadingState variant="skeleton-detail" />;
      }

      if (auth.isAuthenticated) {
        return <MemberShareView token={token} />;
      }
      return <AnonymousShareView token={token} />;
    }
    ```
  - [ ] T7.3 If `AnonymousShareView` was inline (current state), either export it OR extract it (per T5.2 decision). Behavior MUST be preserved exactly for anonymous callers — Story 30.3's chrome additions stay in effect.

- [ ] **T8** (AC-10) — Vitest coverage (6 new tests CR-1/CR-2 + IB-1..4)
  - [ ] T8.1 Create `apps/web/src/routes/share/MemberShareView.test.tsx` covering CR-1 + CR-2.
    - CR-1 uses a mock `useAuth` returning `ANONYMOUS` + memory router → asserts `AnonymousShareView` renders (look for `share.view.brand` "Portal 3D"/"3D Portal").
    - CR-2 uses a mock `useAuth` returning authenticated state + memory router + stubs `/api/me/share-links/<token>/resolve` → asserts `MemberShareView` calls the endpoint + renders the ModelHero title (proves CatalogDetailBody mounted) + info-bar text.
    - Mock pattern for `useAuth`: `vi.mock("@/shell/AuthContext", () => ({ useAuth: vi.fn() }))` then `vi.mocked(useAuth).mockReturnValue({...})` per test.
    - Mock pattern for `api`: per [[feedback_share_view_scope_boundary]] / project-context.md — "Don't mock `api()`; intercept at `fetch` level". Use `vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({...}), {status: 200}))`.
  - [ ] T8.2 Create `apps/web/src/routes/share/ShareMemberContextInfoBar.test.tsx` covering IB-1..IB-4.
    - IB-1: `render(<ShareMemberContextInfoBar modelId="m1" />)` → assert info-bar banner text present.
    - IB-2: render, click dismiss button (`screen.getByRole("button", { name: /dismiss|zamknij/i })`), then assert info-bar text gone (`queryByText` returns null).
    - IB-3: dismiss m1, then mount fresh `<ShareMemberContextInfoBar modelId="m2" />` → info-bar STILL renders (different modelId key).
    - IB-4: `sessionStorage.setItem("share-context-dismissed:m1", "1")` in `beforeEach`, then render m1 → info-bar NOT in DOM on mount.
    - **sessionStorage cleanup**: each test starts from clean sessionStorage. Add `beforeEach(() => sessionStorage.clear())` to the describe block.
  - [ ] T8.3 Per [[feedback_vitest_manual_cleanup]] memory: global `vitest.setup.ts` auto-registers `afterEach(cleanup)` — no per-file boilerplate needed.

- [ ] **T9** (AC-11) — Playwright visual baselines (2 NEW specs × 4 projects = 8 PNGs)
  - [ ] T9.1 Create `apps/web/tests/visual/share-member-enriched.spec.ts`:
    ```typescript
    import { expect, test } from "./_test";

    const TOKEN = "test-token-30-2-enriched";
    const MODEL_ID = "10000000-0000-0000-0000-000000000030";

    const MODEL_DETAIL_FIXTURE = {
      id: MODEL_ID,
      slug: "test-share-30-2",
      name_en: "Test Share Model (Member View)",
      name_pl: "Testowy model udostępniony (widok członka)",
      category: { id: "00000000-0000-0000-0000-000000000c00", slug: "test", name_en: "Test" },
      tags: [],
      files: [],
      external_links: [],
      thumbnail_file_id: null,
      // ...minimal additional fields per ModelDetail shape; reference
      // catalog-detail.spec.ts for the canonical fixture.
    };

    test.describe("Story 30.2 — share view enriched member render", () => {
      test("member opens /share/<token> — sees canonical catalog UI + info-bar", async ({ page }) => {
        // Default api-stubs returns admin; member is a valid subset of "authenticated".
        // Default works; only stub the resolve endpoint + model detail.
        await page.route(`**/api/me/share-links/${TOKEN}/resolve`, (route) =>
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ model_id: MODEL_ID, access: "granted" }),
          }),
        );
        await page.route(`**/api/models/${MODEL_ID}`, (route) =>
          route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(MODEL_DETAIL_FIXTURE),
          }),
        );
        // Stub any other catalog deps that the canonical detail page needs;
        // copy from catalog-detail.spec.ts.

        await page.goto(`/share/${TOKEN}`);
        // Wait for the canonical ModelHero title (proves CatalogDetailBody mounted).
        await page.getByText(MODEL_DETAIL_FIXTURE.name_pl).first().waitFor();

        await expect(page).toHaveScreenshot("share-member-enriched.png", {
          fullPage: false,
          animations: "disabled",
        });
      });
    });
    ```
  - [ ] T9.2 Create `apps/web/tests/visual/share-member-enriched-dismissed.spec.ts` — same setup as T9.1 PLUS `await page.addInitScript((mid) => sessionStorage.setItem("share-context-dismissed:" + mid, "1"), MODEL_ID)` BEFORE `page.goto(...)`. Snapshot captures the enriched view WITHOUT the info-bar.
  - [ ] T9.3 Run `npx playwright test --config=tests/visual/playwright.config.ts --update-snapshots=missing tests/visual/share-member-enriched.spec.ts tests/visual/share-member-enriched-dismissed.spec.ts` from `apps/web/` to generate 8 PNG baselines.
  - [ ] T9.4 Re-run WITHOUT `--update-snapshots` to confirm stability (all 8 should pass on 2nd run).
  - [ ] T9.5 Stage all 8 PNGs in the same commit per FR13. Commit message MUST include `baseline-reviewed: <basename>, Claude (ITCM autonomous, operator AFK), 2026-05-25` line PER PNG.

- [ ] **T10** (full quality gate) — Pre-merge invariants
  - [ ] T10.1 `cd /home/ezop/repos/3d-portal/apps/web && timeout 180 npm run test -- --run` returns green; new vitest count = baseline + 6 (CR-1/2 + IB-1..4).
  - [ ] T10.2 `cd /home/ezop/repos/3d-portal/apps/web && npm run lint && npx tsc --noEmit` returns clean.
  - [ ] T10.3 `cd /home/ezop/repos/3d-portal/apps/web && timeout 300 npm run build` returns green (per [[feedback_pre_merge_gate_checklist]] — full build catches code-split warnings tsc misses; Story 30.2 introduces new component composition + reorders MemberShareView around `CatalogDetailBody`, both of which can affect bundle splits).
  - [ ] T10.4 `cd /home/ezop/repos/3d-portal/apps/web && timeout 300 npx playwright test --config=tests/visual/playwright.config.ts` runs the full visual suite — confirm NO unexpected snapshot diffs in other specs (especially `catalog-detail.spec.ts` — AC-4 invariant).
  - [ ] T10.5 **Pre-merge grep checklist (5 invariants):**
    - [ ] G1 (AC-4 catalog-detail unchanged): `git diff apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/` returns ZERO file diffs.
    - [ ] G2 (NFR10 data-fetch contract unchanged): `grep -nE "credentials:.*omit" apps/web/src/lib/share-api.ts` returns the existing `fetchShareView` line (unchanged).
    - [ ] G3 (i18n parity): `grep -nE "share\.member_context\.(banner|open_in_catalog|dismiss_aria)" apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns 6 hits (3 keys × 2 files).
    - [ ] G4 (no redirect to /catalog from MemberShareView): `grep -nE "navigate\(.*catalog" apps/web/src/routes/share/MemberShareView.tsx` returns ZERO hits.
    - [ ] G5 (AuthContext gate fully removed): `grep -nE "isAnonymousShareRoute|!isAnonymousShareRoute" apps/web/src/shell/AuthContext.tsx` returns ZERO hits.

- [ ] **T11** (handoff to deploy + close-out)
  - [ ] T11.1 Story file Dev Agent Record gets file list (10+ files expected: AuthContext.tsx MOD + AppShell.tsx MOD + CatalogDetail.tsx MOD + $token.tsx MOD + en.json MOD + pl.json MOD + MemberShareView.tsx NEW + ShareMemberContextInfoBar.tsx NEW + useShareResolve.ts NEW + 2 visual spec NEW + 8 PNGs NEW + 2 vitest files NEW/EXTEND).
  - [ ] T11.2 Sprint-status flip `30-2-conditional-render-member-share-view-info-bar: ready-for-dev → in-progress → review → done` per BMAD convention.
  - [ ] T11.3 Auto-deploy to `.190` per [[feedback_auto_deploy_dev]] (this is code change; full `deploy.sh` post-merge).
  - [ ] T11.4 Post-deploy operator verification (AFTER merge but operator may be AFK — note in commit message): Ezop logs in as member, opens own share-link in same browser → expects to see canonical catalog detail UI + info-bar. Acceptance test that closes the Init 18 use-case-enumeration gap.
  - [ ] T11.5 Note in commit message: closes the post-Init-12 use-case-enumeration gap surfaced 2026-05-24 (B5 member receiving share link now sees full canonical experience). Phase B (anonymous CONTENT parity) remains deferred per [[feedback_share_view_scope_boundary]] amended carve-out.

## Dev Notes

### Source-of-truth references

- **PRD:** `prd.md` § Initiative 18 — FR18-FE-CONDITIONAL-RENDER-1, FR18-MEMBER-SHARE-VIEW-1, FR18-INFO-BAR-1, NFR18-VISUAL-VERIFICATION-1, NFR18-I18N-PARITY-1.
- **Architecture:** `architecture.md` § Initiative 18 Decisions AB + AC.
- **SCP:** `sprint-change-proposal-2026-05-25-init18.md` § §4.1-§4.3 (Story 30.2 entry).
- **UX rec:** `share-flow-membership-path-ux.md` Deliverable 2 (Variant γ + ASCII mockup + Tailwind classes for info-bar) + Deliverable 4 (visual diff member-view at `/share/<token>` vs `/catalog/$id`).
- **Brainstorm:** `brainstorming-session-2026-05-25-0030.md` § Phase 3 cross-pollination (enrich-in-place pattern from GitHub/Nextcloud/Notion) + α-2 (deep-link to specific model — handled by passing model_id from resolve endpoint) + rα-1 (URL stability mitigation by design).
- **Memory entries (mandatory):**
  - [[feedback_share_view_scope_boundary]] (amended 2026-05-25 carve-out) — B5 enrich-in-place IS NOT share-view content enrichment, it's membership-path completion; visual baseline regen for the NEW B5 render is warranted.
  - [[feedback_frontend_visual_verification]] — Story 30.2 carries 8 NEW PNG baselines per FR13.
  - [[feedback_codex_model_routing]] — Story 30.2 routed to `gpt-5.4-mini`.
  - [[feedback_pre_merge_gate_checklist]] — T10 pre-merge invariants list.
  - [[feedback_vitest_manual_cleanup]] — global vitest.setup.ts auto-registers afterEach(cleanup); T8 inherits.
  - [[feedback_lazy_import_discipline]] — `CatalogDetailBody` is reused (NOT lazy-loaded in MemberShareView) — same chunk affinity as `/catalog/$id` route; no new code-split needed.
  - [[feedback_shared_cache_in_react]] — `useShareResolve` is a per-token `useQuery` (no module-level cache); StrictMode-safe by React Query design.
  - [[feedback_auth_boundary_contract_audit]] — T1 (AuthContext loosening) DOES touch the auth boundary indirectly; documented as Init 18 Decision AB carve-out from Init 10 NFR10-SHARE-SECURITY-1, with the explicit reasoning that NFR10 protects `/api/share/<token>/*` data endpoints (still credentialless via `fetchShareView`), NOT `/api/auth/me` (which is a separate cross-cutting concern).

### CRITICAL: Pre-enumeration finding 2026-05-25 (AuthContext NFR10 carve-out)

Per pre-enumeration phase before SCP draft (memory [[feedback_scp_pre_enumeration_phase]]):

**`apps/web/src/shell/AuthContext.tsx:82-122` disables `/auth/me` on `/share/*` routes** via `enabled: !isAnonymousShareRoute` + ANONYMOUS short-circuit. This was implemented for Init 10 Story 16.3 NFR10-SHARE-SECURITY-1 — share view should be anonymous-by-design even for logged-in users (so the share link looks identical to authenticated and anonymous recipients, preventing inadvertent auth-state leakage in screenshots).

**Init 18 EXPLICITLY REVERSES this carve-out** because the new B5 use case (active member receiving share link) DEPENDS on the system recognizing the recipient's authenticated state. Without re-enabling `/auth/me` on `/share/*`, the conditional render in AC-1 will never trigger the member branch — `useAuth()` will always return ANONYMOUS.

The reversal is safe because:
1. **NFR10 data contract is unchanged**: `/api/share/<token>/*` (the data endpoints) still go through `fetchShareView` with `credentials: "omit"` — Story 30.2 does NOT touch `share-api.ts`.
2. **The "anonymous-by-design even when logged in" property was over-conservative for Init 10's actual goal**: the goal was preventing cookie attachment to share-asset endpoints, which is enforced at the `fetchShareView` level, not at AuthContext gating.
3. **Init 18 Decision AB is a deliberate scope change**: B5 enrich-in-place IS the feature; the Init 10 gating is in tension with that feature, and the correct resolution is to remove it.

**Operational implication for the dev agent**: AuthContext.test.tsx (if it exists and asserts on the share-route ANONYMOUS short-circuit) will fail and needs updating per T1.5 — those test assertions encode the Init 10 invariant that Init 18 explicitly reverses. Update the test to verify the new behavior + add a comment referencing Init 18 Decision AB.

### Files this story touches

| File | Action | Why |
|---|---|---|
| `apps/web/src/shell/AuthContext.tsx` | MODIFY (remove `/share/*` gating) | T1 — Decision AB carve-out from Init 10 NFR10 (per AC-7) |
| `apps/web/src/shell/AuthContext.test.tsx` | MODIFY (update Init 10 share-route assertions if present) | T1.5 |
| `apps/web/src/shell/AppShell.tsx` | MODIFY (conditional bypass per Decision AB) | T2 |
| `apps/web/src/modules/catalog/routes/CatalogDetail.tsx` | MODIFY (extract `CatalogDetailBody`) | T3 — pure refactor, zero behavior change |
| `apps/web/src/routes/share/$token.tsx` | MODIFY (`ShareTokenRoute` split + export `AnonymousShareView` or extract) | T7 |
| `apps/web/src/routes/share/useShareResolve.ts` | CREATE | T4 — new hook wrapping resolve endpoint |
| `apps/web/src/routes/share/MemberShareView.tsx` | CREATE | T5 — new component |
| `apps/web/src/routes/share/MemberShareView.test.tsx` | CREATE | T8 — CR-1 + CR-2 |
| `apps/web/src/routes/share/ShareMemberContextInfoBar.tsx` | CREATE | T6 — new component |
| `apps/web/src/routes/share/ShareMemberContextInfoBar.test.tsx` | CREATE | T8 — IB-1..IB-4 |
| `apps/web/src/locales/en.json` | MODIFY (+3 keys) | T6.2 |
| `apps/web/src/locales/pl.json` | MODIFY (+3 keys) | T6.3 |
| `apps/web/tests/visual/share-member-enriched.spec.ts` | CREATE | T9.1 |
| `apps/web/tests/visual/share-member-enriched-dismissed.spec.ts` | CREATE | T9.2 |
| `apps/web/tests/visual/__snapshots__/share-member-enriched*/share-member-enriched*.png` | CREATE (8 PNGs) | T9.3 |

**Files this story MUST NOT touch:**

- `apps/web/src/lib/share-api.ts` — NFR10 credentialless data contract preserved (G2 invariant).
- `apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/*` — AC-4 invariant: refactor MUST be behavior-preserving.
- `apps/api/app/modules/share/*` — backend Story 30.1 owns those; Story 30.2 is pure FE consumption.
- Story 30.3's `SignInButton.tsx` — chrome additions live on the anonymous render only; member view uses TopBar's `UserMenu` for the equivalent affordance (already exists).

### Conventions to follow (recap from project-context.md)

- **`api()` wrapper for authenticated calls** — `useShareResolve` uses `api()` (not raw fetch).
- **NO inline hex colors** — all components use CSS-token Tailwind classes.
- **i18n parity** — 3 new keys in BOTH en+pl.
- **Visual regression mandatory** — 8 PNGs × 4 projects per FR13.
- **Conventional commit** — `feat(share): conditional render + MemberShareView + info-bar (Story 30.2, Init 18)`.

### Project Structure Notes

- All new files colocated under `apps/web/src/routes/share/` (consistent with `SignInButton.tsx` from Story 30.3 + existing `shareBlobCache.ts`).
- `useShareResolve.ts` is share-flow-specific; not promoted to `@/lib/` until a second caller needs it (YAGNI).
- `CatalogDetailBody` extraction is the only cross-module touch; live in the canonical catalog detail file for discoverability.

### References

- [Source: `apps/web/src/shell/AuthContext.tsx:82-122`] — current Init 10 `/share/*` gating to remove (AC-7 + T1).
- [Source: `apps/web/src/shell/AppShell.tsx:60`] — current unconditional bypass to make conditional (AC-6 + T2).
- [Source: `apps/web/src/modules/catalog/routes/CatalogDetail.tsx`] — body to extract into `CatalogDetailBody` (AC-4 + T3).
- [Source: `apps/web/src/modules/catalog/hooks/useModel.ts`] — `useModel(id)` is the auth-bound data hook the new `MemberShareView` reuses via `CatalogDetailBody`.
- [Source: `apps/web/src/routes/share/$token.tsx:571`] — `ShareTokenRoute` to modify (AC-1 + T7).
- [Source: `apps/web/src/routes/share/$token.tsx:408`] — `AnonymousShareView({ token })` signature — colocate or export for `MemberShareView` fallback path (T5.1).
- [Source: `apps/web/src/lib/share-api.ts:78-94`] — `fetchShareView` with `credentials: "omit"` — the NFR10 data-fetch contract that STAYS intact (G2 invariant).
- [Source: `apps/web/src/lib/api.ts`] — `api()` wrapper used by `useShareResolve` for authenticated calls.
- [Source: `apps/web/tests/visual/catalog-detail.spec.ts`] — existing canonical model-detail spec; copy stub patterns for the new `share-member-enriched*` specs.
- [Source: `apps/web/tests/visual/_test.ts:39-50`] — default `/api/auth/me` returns admin in visual fixture; member is a valid subset (no override needed for Story 30.2's enriched visual specs).
- [Source: `apps/web/src/routes/share/SignInButton.tsx`] — Story 30.3 colocation pattern (sibling route file under `apps/web/src/routes/share/`).
- [Source: `apps/web/src/routes/share/SignInButton.test.tsx`] — Story 30.3 router-wrapped vitest pattern (memory history + createRoute) — `MemberShareView.test.tsx` mirrors this for navigation assertions.
- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 18 Decision AB] — conditional AppShell bypass rationale + implementation sketch (AC-6).
- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 18 Decision AC] — sessionStorage info-bar dismissal rationale + edge-case handling (AC-5).
- [Source: `_bmad-output/ux/share-flow-membership-path-ux.md` Deliverable 2] — ASCII mockup of Variant γ render + info-bar Tailwind classes + copy.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) via bmad-dev-story skill

### Debug Log References

(populated by dev-story execution)

### Completion Notes List

(populated by dev-story execution)

### File List

(populated by dev-story execution — expected: ~13 files modified/created + 8 PNGs)

- apps/web/src/shell/AuthContext.tsx (MOD: remove /share/* gating per Init 18 Decision AB)
- apps/web/src/shell/AuthContext.test.tsx (MOD if Init 10 share-route assertions present)
- apps/web/src/shell/AppShell.tsx (MOD: conditional bypass per Decision AB)
- apps/web/src/modules/catalog/routes/CatalogDetail.tsx (MOD: extract CatalogDetailBody)
- apps/web/src/routes/share/$token.tsx (MOD: ShareTokenRoute split + export AnonymousShareView)
- apps/web/src/routes/share/useShareResolve.ts (NEW)
- apps/web/src/routes/share/MemberShareView.tsx (NEW)
- apps/web/src/routes/share/MemberShareView.test.tsx (NEW: CR-1/CR-2)
- apps/web/src/routes/share/ShareMemberContextInfoBar.tsx (NEW)
- apps/web/src/routes/share/ShareMemberContextInfoBar.test.tsx (NEW: IB-1..IB-4)
- apps/web/src/locales/en.json (MOD: +3 keys)
- apps/web/src/locales/pl.json (MOD: +3 keys)
- apps/web/tests/visual/share-member-enriched.spec.ts (NEW)
- apps/web/tests/visual/share-member-enriched-dismissed.spec.ts (NEW)
- apps/web/tests/visual/__snapshots__/share-member-enriched.spec.ts/*.png (NEW × 4)
- apps/web/tests/visual/__snapshots__/share-member-enriched-dismissed.spec.ts/*.png (NEW × 4)
