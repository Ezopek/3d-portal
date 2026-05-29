---
artifact: ux-recommendation
topic: share-flow-membership-path-completion
designer: Sally
date: 2026-05-25
input_brainstorm: _bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md
downstream: bmad-correct-course (policy amendment + PRD/SCP)
status: ready-for-operator-review
---

# Share-Flow UX Recommendation — Membership-Path Completion

**Author:** Sally (UX Designer) — 2026-05-25
**Predecessor:** Brainstorming session locked Path α (intent-blind), 2 render modes + 1 future. This document adds the visual / copy / interaction layer.

## TL;DR (status: all operator decisions resolved 2026-05-25)

1. **"Sign in" + LangToggle + ThemeToggle in share-view header** — combined right-side control group: `[brand] · Oglądasz udostępniony model · [🌙] [PL] [⤷ Zaloguj się]`. Same control order as member TopBar. Operator-approved as carve-out from share-view-terminus policy (Decisions 1+2).
2. **B5 enrich-in-place:** **Variant γ** — render canonical member catalog detail UI at `/share/<token>`, plus a dismissible info-bar at top of main content: *"Otworzyłeś ten model z linku udostępnionego · Otwórz w katalogu"*. Dismissal in sessionStorage per-model (Decision 3 approved).
3. **Copy:** `Zaloguj się` / `Sign in` — single string, no audience-targeted variant. Friends-and-family tone, no emoji, optional `LogIn` lucide icon.
4. **Visual diff (member-view at `/share/<token>` vs `/catalog/<id>`):** identical except the info-bar in (2). URL stays `/share/<token>` for bookmark stability.

**Out-of-scope for this initiative (operator-deferred 2026-05-25 — Phase B):** share-view CONTENT parity (description placement, multi-STL listing, fullscreen 3D viewer for anonymous). These would require a full reversal — not carve-out — of the share-view-terminus policy, plus their own brainstorm pass for security/NFR10 implications. Tracked separately for a future initiative.

## Constraints in force (verbatim from brainstorm)

- One SHARE button, one URL shape (Path β killed).
- Anonymous share-view content layout/gallery/description/STL/viewer behavior — UNTOUCHED per share-view-terminus policy.
- No self-serve registration CTA, no native app handoff, no action-bridge UI.
- Sender does not signal intent — routing is recipient-state-only.

## Current state (read from code, 2026-05-25)

Share-view at `/share/$token` renders a minimal header:

```
┌──────────────────────────────────────────────────────┐
│ Portal 3D                Oglądasz udostępniony model │  ← existing header
├──────────────────────────────────────────────────────┤
│ [category text]                                       │
│ Model title                                           │
│ [tag chips]                                           │
│                                                       │
│ [Carousel — single image + thumb strip + chevrons]    │
│                                                       │
│ ┌─── STL section ───────────────────────────────┐    │
│ │ Plik 3D                                        │    │
│ │ [inline 3D viewer]                             │    │
│ │ Pobierz STL, aby wydrukować…                  │    │
│ │ [Pobierz STL button]                           │    │
│ └────────────────────────────────────────────────┘    │
│                                                       │
│ ┌─── Description section ───────────────────────┐    │
│ │ Opis                                           │    │
│ │ [notes text]                                   │    │
│ └────────────────────────────────────────────────┘    │
│                                                       │
│ To jest udostępniony link — Twoje wyświetlenie...    │  ← anonymous footer notice
└──────────────────────────────────────────────────────┘
```

**Header today:** brand on left, banner text on right. No language toggle, no theme toggle, no Sign in affordance.

**Architectural facts confirmed from code:**

- Route file: `apps/web/src/routes/share/$token.tsx`.
- AppShell bypasses ModuleRail+TopBar for `/share/*` (per `_PUBLIC_PATHS` in `AppShell.tsx`).
- Share-view explicitly renders its own minimal `<header>` instead.
- Canonical member catalog detail lives at `/catalog/$id` (NOT `/collections/<id>` as the operator's original message named).
- TopBar (member chrome) wires `ThemeToggle + LangToggle + UserMenu` on the right.
- Existing i18n keys live under `share.view.*` in `apps/web/src/locales/{en,pl}.json` — adding new keys requires both files.

## Deliverable 1 — "Sign in" affordance placement

### Alternatives evaluated

| Option | Placement | Pros | Cons | Verdict |
|---|---|---|---|---|
| **(a)** Right-side button, combined with banner text | `[brand] ········ Oglądasz udostępniony model · [Zaloguj się]` | Mirrors member TopBar's right-aligned action; Notion/GitHub precedent; preserves existing banner context for B1/B2; single chrome row | Slight horizontal crowding on narrow viewports → needs responsive collapse | **RECOMMENDED** |
| (b) Inline banner below header | Extra row under header with full-width info+CTA | Maximum visibility | Adds vertical chrome; tilts toward "share-view enrichment" feel; conflicts with terminus restraint | Reject |
| (c) Floating action button | Bottom-right FAB | Not missable | Modal-feeling for what should be ambient; conflicts with friends-and-family minimalism | Reject |
| (d) End-of-content CTA | After footer | Doesn't impose | Too late, easy to miss; defeats purpose | Reject |

### Recommended placement (Option a) — ASCII mockup

**Desktop ≥ 640px:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Portal 3D       Oglądasz udostępniony model · [ ⤷ Zaloguj się ] │
├──────────────────────────────────────────────────────────────────┤
│ ...same content as today (untouched per terminus policy)...      │
```

**Mobile < 640px:**

The banner text wraps below brand; the Sign in button stays right-aligned on its own row. Banner text MAY collapse to icon-only (`ⓘ` + tooltip) if horizontal space is too tight.

```
┌──────────────────────────────────┐
│ Portal 3D     [ ⤷ Zaloguj się ] │
│ Oglądasz udostępniony model      │
├──────────────────────────────────┤
│ ...content...                    │
```

### Visual specification

- Element: `<button type="button">` styled as a small secondary action (NOT primary — that would over-emphasize against share-view's intentionally calm chrome).
- Tailwind classes (using existing tokens): `inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring`.
- Icon: `LogIn` from `lucide-react` (already a project dep), `size-4` left of label.
- Behavior: navigate to `/login?returnTo=/share/<token>` (Story spec must implement return-URL flow per brainstorm α-5).
- aria-label: same as visible label — no extra ARIA decoration needed.

### Why combine banner text with CTA instead of replacing it

Operator's original message asked for the button **next to** the banner text, not as a replacement. The banner serves a different purpose for each recipient:

- **B1/B2** (no account): banner is the only signal that this is share-context, not a personal catalog. Removing it would confuse them.
- **B3/B4** (absentee-member): banner + button together form an internally-consistent affordance — "you're on a shared link, but you can sign in if you have an account".

Replacing one with the other forces an either/or trade. Combining them costs ~10 horizontal pixels and serves both audiences correctly.

## Deliverable 2 — B5 enrich-in-place pattern

### Three variants evaluated

| Variant | Description | Pros | Cons |
|---|---|---|---|
| **α — Full member view at share URL** | At `/share/<token>` for B5, render the same component tree as `/catalog/$id` does for B5. No mention of "share context". | Architecturally trivial (route-level conditional render swaps the component); zero new chrome to design; B5 gets full canonical experience | Recipient has no signal they came via share-link → may bookmark `/share/<token>` thinking it's THEIR canonical URL → if sender revokes link, bookmark dies silently |
| **β — Share-view content + member chrome wrapper** | Wrap existing `AnonymousShareView` in AppShell+TopBar+ModuleRail. Keep share-specific content layout. | Maintains brainstorm's "share-view shell stays visible" framing | DOWNGRADES B5's experience — they get share-view content (no comments, no member actions, no canonical gallery) instead of richer member-view they have access to. Anti-pattern: punishing the more-entitled user. |
| **γ — Member view + dismissible "from-share" info-bar** | Render full canonical catalog detail UI; add one thin dismissible info-bar at top of main content: "You opened this from a shared link · Open in catalog". URL stays `/share/<token>`. | Full canonical content (no downgrade); URL stability (no redirect); explicit share-context signal (no silent bookmark trap); explicit affordance to switch to canonical bookmark; matches brainstorm rα-1 mitigation directly | One small additional component to maintain (the info-bar); ~32px of vertical chrome until dismissed |

### Recommended: Variant γ

The info-bar resolves the only meaningful weakness of Variant α (silent bookmark trap) and the structural problem of Variant β (downgrading B5's content). Cost is minimal (one component, dismissible, ~32px).

### ASCII mockup — Variant γ rendered at `/share/<token>` for B5

```
┌──────────────────────────────────────────────────────────────────┐
│ [ModuleRail title]     [Theme] [Lang] [UserMenu: Ezop avatar]    │  ← full TopBar
├──┬───────────────────────────────────────────────────────────────┤
│  │                                                                │
│ M│ ┌──────────────────────────────────────────────────────────┐  │
│ o│ │ ℹ️  Otworzyłeś ten model z linku udostępnionego.        │  │  ← info-bar (Variant γ)
│ d│ │     [ Otwórz w katalogu ]                       [×]      │  │     dismissible
│ u│ └──────────────────────────────────────────────────────────┘  │
│ l│                                                                │
│ e│ [ModelHero — full member version: title, owner, status, tags]  │
│  │                                                                │
│ R│ [ModelGallery — full member version: photos with full viewer]  │
│ a│                                                                │
│ i│ [STL files — full list with viewers and member actions]        │
│ l│                                                                │
│  │ [Description block — member layout]                            │
│  │ [Comments / actions — whatever the member catalog detail has]  │
└──┴────────────────────────────────────────────────────────────────┘
```

### Info-bar specification

- Component: shadcn `Alert` primitive (or equivalent), `variant="default"` (NOT destructive / warning — informational only).
- Tailwind: `mb-4 flex items-center justify-between gap-3 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm`.
- Icon: `Info` from `lucide-react`, `size-4`, muted-foreground color.
- Action: `<Link to="/catalog/$id" params={{ id: model.id }}>Otwórz w katalogu</Link>` — TanStack Router-typed link.
- Dismissal: close button on the right; state stored in `sessionStorage` with key `share-context-dismissed:<modelId>` so dismissal sticks for the session but re-shows for different models or new sessions. Operator may downgrade to `localStorage` if "forever dismissed" is preferred — Sally's pick is sessionStorage for less surprise.

### Why URL stays `/share/<token>` (not redirect to `/catalog/$id`)

This is the brainstorm's locked decision (C2' "enrich-in-place"), confirmed by cross-platform convention. The info-bar gives the recipient a one-click path to canonical URL if they want it. Forced redirect would:

- Break back-button (recipient who clicked the link from a chat app expects "back" to return to the chat, not to the share URL).
- Defeat bookmarking the share-link from address bar (sender might want to re-share with friends-and-family).
- Conflict with the rα-1 mitigation framing.

### Architectural note for the dev story

The conditional render lives at the route component level (`apps/web/src/routes/share/$token.tsx`). Sketch:

```tsx
function ShareTokenRoute() {
  const { token } = Route.useParams();
  const { user } = useAuth();
  if (user !== null) {
    // B5 active session → enrich-in-place
    return <MemberShareView token={token} />;
  }
  // B1/B2/B3/B4/B6 → anonymous render (today's AnonymousShareView)
  return <AnonymousShareView token={token} />;
}
```

`MemberShareView` resolves the token → model id via a NEW authenticated endpoint (e.g. `GET /api/share/<token>/resolve` returning `{model_id}` if the caller is authenticated; or extend the existing share-view endpoint to recognize sessions and respond with model_id + a flag). Then it renders the canonical catalog detail component tree with the model id, plus the info-bar.

Backend implication (for correct-course / dev story): the existing `/api/share/<token>` endpoint MUST stay credentialless and anonymous for B1-B4 callers (NFR10-SHARE-SECURITY-1 contract). The "is this caller authenticated and has access to this model" check is a NEW endpoint or a new branch — not a modification of the public bypass. Frontend should call the new branch only when `useAuth()` reports a session, so the credentialless contract for anonymous flows is untouched.

## Deliverable 3 — Copy guidance

### Sign in CTA

| Audience | Recommended copy | Why |
|---|---|---|
| Single string for ALL (B1/B2/B3/B4) | **PL: "Zaloguj się"** / **EN: "Sign in"** | Notion/GitHub precedent: minimal terse copy. B1/B2 ignore it naturally (they have nothing to log in to); B3/B4 act on it. Audience-targeted variants ("Have an account? Sign in") imply upselling and clash with friends-and-family tone. |

**Tone notes:**

- No emoji (operator preference + project banking-DevOps register).
- Optional `LogIn` lucide icon (already in project deps) for scanability — Sally recommends YES.
- Sentence case in PL ("Zaloguj się" — verb + reflexive particle, natural Polish imperative for self-action), NOT all-caps (corporate feel).
- Avoid "Wejdź do panelu" / "Enter dashboard" — too feature-portal; conflicts with friends-and-family register.

### Info-bar copy (B5 Variant γ)

| Element | PL | EN |
|---|---|---|
| Banner text | "Otworzyłeś ten model z linku udostępnionego." | "You opened this model from a shared link." |
| Action link | "Otwórz w katalogu" | "Open in catalog" |
| Dismiss aria | "Zamknij informację" | "Dismiss notice" |

**Why this copy:**

- "Otworzyłeś ten model z linku udostępnionego" is past-tense matter-of-fact — informative, not nagging.
- "Otwórz w katalogu" is action-imperative — short, scannable, mirrors member nav language already in the app.
- Avoids "Click here to go to your collection" tone — operator's friends-and-family register prefers concise verbs.

### Proposed i18n keys (additions to `apps/web/src/locales/{en,pl}.json`)

```json
{
  "share.view.signin_cta": "Zaloguj się" / "Sign in",
  "share.view.signin_aria": "Zaloguj się, aby zobaczyć więcej opcji" / "Sign in to access more options",
  "share.member_context.banner": "Otworzyłeś ten model z linku udostępnionego." / "You opened this model from a shared link.",
  "share.member_context.open_in_catalog": "Otwórz w katalogu" / "Open in catalog",
  "share.member_context.dismiss_aria": "Zamknij informację" / "Dismiss notice"
}
```

Both `en.json` and `pl.json` MUST include all 5 keys per project-context.md i18n rule.

## Deliverable 4 — Visual diff: member-view at `/share/<token>` vs `/catalog/$id`

**Identical:** AppShell + TopBar (Theme + Lang + UserMenu) + ModuleRail + ModelHero + ModelGallery (full member gallery with fullscreen viewer) + STL file list with viewers + description block + any comments / member actions / metadata blocks that exist on `/catalog/$id`.

**Different — single element:** the dismissible info-bar at top of main content area (specified above in Deliverable 2).

**URL:** stays `/share/<token>`. The info-bar's "Otwórz w katalogu" link is the explicit affordance to switch to `/catalog/$id` if the recipient wants the canonical URL for bookmarking.

**Should the user receive a "you came from share" signal?** YES, but minimal and dismissible. Reasoning:

- Without signal (Variant α): silent bookmark trap (described above).
- With persistent badge: visual noise on canonical-equivalent content.
- With dismissible info-bar: signal once, then user moves on — best balance.

## Operator-level open question (Sally's answer)

> *"Czy 'Sign in' affordance powinno mieć też wariant 'Założyłeś konto? Sprawdź swój model w panelu' dla B5?"*

**NO.** Strong opinion. Reasoning:

- B5 user is already logged in; they don't see "Sign in" at all (it's only in the anonymous render).
- The Variant γ info-bar already provides the "go to canonical view" affordance ("Otwórz w katalogu" link).
- Adding a second CTA ("Sprawdź swój model w panelu") would be redundant + nag-feeling.
- The full member-chrome (UserMenu in TopBar, ModuleRail visible) already signals "you're logged in as YOU" — no extra reminder needed.

If operator wants a stronger pull toward canonical URL (e.g. analytics show many users staying on `/share/<token>` permanently), the info-bar text can become slightly more action-oriented in a future iteration. But initial spec should be informational, not prescriptive.

## Operator decisions — RESOLVED 2026-05-25

### Decision 1 — Sign in button carve-out → **APPROVED**

Operator (2026-05-25): adding "Sign in" button to share-view chrome is a carve-out from `feedback_share_view_scope_boundary` terminus policy. Justification: button is structurally an affordance pointing AWAY from share-view (toward membership-path completion), not enriching share-view content/feature surface.

`bmad-correct-course` deliverable: amend `feedback_share_view_scope_boundary.md` with explicit carve-out language preserving the original terminus for share-view CONTENT while permitting the Sign in affordance in CHROME.

### Decision 2 — LangToggle + ThemeToggle on share-view chrome → **APPROVED (both)**

Operator (2026-05-25): add BOTH `LangToggle` and `ThemeToggle` to the minimal share-view header alongside Sign in. Same carve-out logic as Decision 1 — these are infrastructure-level UI primitives (how user consumes content), not share-view feature enrichment.

Final share-view header mockup (desktop):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Portal 3D   Oglądasz udost. model · [🌙 Theme] [PL Lang] [⤷ Zaloguj się] │
├─────────────────────────────────────────────────────────────────────────────┤
```

The three controls (Theme, Lang, Sign in) follow the same right-side order as the member TopBar (`ThemeToggle + LangToggle + UserMenu`) — recipient who switches between share-view and member-view sees consistent affordance ordering.

Mobile collapse: same responsive treatment as the member TopBar — Sign in button gets its own row below brand+banner, with Lang+Theme as icon-only buttons grouped to its left.

`bmad-correct-course` deliverable: extend the carve-out amendment to cover Lang+Theme toggles in addition to Sign in. All three are CHROME affordances, not CONTENT enrichment.

### Decision 3 — Info-bar dismissal persistence → **APPROVED (sessionStorage per-model)**

Operator (2026-05-25): dismissal state stored in `sessionStorage` with key pattern `share-context-dismissed:<modelId>`. Next session re-shows the info-bar (assumes user may have forgotten the context).

## Implementation hooks for `bmad-correct-course`

When the correct-course skill drafts the PRD / SCP / sprint plan, it should reference:

- **Backend:** new authenticated branch on the share-resolve flow that returns `model_id` + access-confirmation for sessions with active cookie, while keeping `/api/share/<token>/*` credentialless for anonymous callers (NFR10 contract preservation is critical).
- **Frontend route:** `apps/web/src/routes/share/$token.tsx` conditional render based on `useAuth()` result.
- **Frontend component:** new `MemberShareView` (or equivalent) that wraps the canonical catalog detail component tree + the dismissible info-bar.
- **Frontend chrome:** modify the share-view header to include `LangToggle + ThemeToggle + SignInButton` (per Decision 2 if approved, only `SignInButton` if not).
- **Login flow:** implement return-URL parameter in `/login` route so `/login?returnTo=/share/<token>` returns user to share-link post-login (covers brainstorm α-5).
- **i18n:** add 5 new keys to `en.json` + `pl.json`.
- **Visual tests:** add Playwright snapshot specs for the new states (anonymous-with-signin, B5-enriched-with-info-bar, B5-enriched-info-bar-dismissed). Per project-context.md mandate, all 4 visual projects (desktop-light, desktop-dark, mobile-light, mobile-dark).
- **Story breakdown estimate:** 3 stories — (1) backend resolve branch + return-URL flow; (2) frontend conditional render + MemberShareView + info-bar; (3) frontend chrome additions (Sign in + maybe toggles per Decision 2).

## Out-of-scope reminders (do NOT include in correct-course unless operator amends further)

- B7 future granular sharing → "Request access" page (defer until granular sharing feature exists).
- B6 disabled-account handling beyond "fall through to anonymous" (defer until disabled-account usage data exists).
- Multi-tab race / session-expiry-mid-view / mid-session account creation (α-3, α-4, α-6) — handle ad-hoc per operator's brainstorm decision.
- Cross-cutting edge cases x-1 through x-8 — handle ad-hoc.

---

**Sally's exit handoff:** this document is ready to feed `bmad-correct-course` along with the brainstorm output. Operator should resolve Decisions 1-3 explicitly before correct-course starts so the PRD / SCP scope is unambiguous.
