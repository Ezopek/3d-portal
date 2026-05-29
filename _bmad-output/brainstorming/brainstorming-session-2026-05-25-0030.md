---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Share-flow use-case enumeration for /share/<token> — full decision-tree across sender intent × recipient state × system action'
session_goals: '(1) Raw material for Sally (bmad-agent-ux-designer) to ground UX best-practice recommendation for share/invite/cross-account-handoff pattern; (2) Concrete scope decisions for bmad-correct-course (amend vs reverse share-view-terminus policy from 2026-05-23 vs status-quo + new membership-routing subtree)'
selected_approach: 'AI-recommended'
techniques_used: ['Decision Tree Mapping', 'What If Scenarios', 'Reverse Brainstorming', 'Cross-Pollination']
ideas_generated: 23
context_file: ''
workflow_completed: true
---

# Brainstorming Session Results

**Facilitator:** Ezop
**Date:** 2026-05-25

## Session Overview

**Topic:** Share-flow use-case enumeration for `/share/<token>` — full decision-tree across sender intent × recipient state × system action.

**Goals:**
1. Raw material for Sally (`bmad-agent-ux-designer`) to ground UX best-practice recommendation for the share / invite / cross-account-handoff pattern.
2. Concrete scope decisions for `bmad-correct-course`: amend vs reverse the share-view-terminus policy from 2026-05-23, vs keep status-quo and add a new membership-routing subtree.

### Context Guidance

Post-ship gap surfaced 2026-05-24: the `/share/<token>` feature (shipped through Init 6+12) was designed under the implicit assumption of anonymous-only recipients. Reality has at least three recipient states (no-account-anonymous, has-account-not-logged-in, has-account-logged-in-elsewhere), and the system currently treats all three identically, producing a degraded experience for state #3. Quick-fix proposals (auto-redirect, login CTA, share-button copy clarity) were retrofitted plasters; this session re-opens the use-case space from inception-stage rigour.

**Hard constraints in force during this session:**
- Share-view content/UX is NOT being enriched for anonymous recipients (policy 2026-05-23 stands during the session; whether to amend is a downstream `bmad-correct-course` decision, not a brainstorm decision).
- Recipient-routing-to-existing-member-view is treated as membership-path completion, NOT share-view enrichment.
- Sender cannot be required to know recipient's account state at link-generation time.

### Session Setup

- **Approach:** AI-recommended techniques.
- **Communication language:** Polish (with operator).
- **Document output language:** English (this file).

## Technique Selection

**Approach:** AI-Recommended Techniques

**Recommended sequence:**

1. **Decision Tree Mapping** (structured) — Phase 1, Foundation. Build the structural skeleton: sender intent × recipient state × system action. Surfaces named branches and provides the substrate for edge-case hunting in Phase 2.
2. **What If Scenarios + Reverse Brainstorming** (creative) — Phase 2, Idea Generation. Stress-test the Phase 1 tree against unnamed edge cases (wrong-account login, cross-device sessions, link-via-screenshot, transient sessions, etc.) and ask "how could the current design fail most spectacularly" to surface hidden assumptions.
3. **Cross-Pollination** (creative) — Phase 3, Refinement. Transfer known-pattern solutions from Google Docs / Notion / Figma / Dropbox / GitHub / Twitter / Instagram for the "share-link reaches known account" pattern. Output directly feeds Sally's UX best-practice recommendation.

**AI Rationale:** Topic is a structural enumeration problem requiring both rigour (Phase 1 + 2 catch missed branches) and prior-art transfer (Phase 3 grounds downstream UX work in known patterns). Sequence balances structured analysis with creative edge-case generation while keeping total session ≤45 min within the operator's 5h token budget.

## Phase 1 — Decision Tree Mapping

### Axis A: Sender Intent (why the link-creator clicked SHARE)

Locked after operator pruning (A3, A4, A7 removed — covered by other planned/existing mechanisms: portal-native admin actions, favourites/bookmarks, external comm channels respectively):

- **A1 — Show to friend/family outside portal** (no-account recipient assumed). Original design assumption.
- **A2 — Show to another portal member** (covers both pure-show AND requests that travel via external comm channels like SMS/Messenger after the share). The 2026-05-24 gap.
- **A5 — Public publication** (forum, social media, link with no specific recipient).
- **A6 — Show prospect / pre-sales** (potential future member, not invited yet).

### Axis B: Recipient State (in what state recipient lands on the link)

Operator confirmed all 7 states are real; B7 reserved for future granular-sharing feature. Engineering collapse below addresses what the system can actually detect at request time:

- **B1 — Anonymous, never-visited**
- **B2 — Anonymous, visited-before**
- **B3 — Has account, NOT logged in this browser/session**
- **B4 — Has account, logged in DIFFERENT browser/device**
- **B5 — Has account, ACTIVE session this browser**
- **B6 — Has account but DISABLED/inactive**
- **B7 — Has account but NO ACCESS to this model** (future granular-sharing feature)

**Engineering collapse (system-detectable distinct states):**

- B1 + B2 → **"anonymous"** (system cannot reliably distinguish first-vs-repeat anonymous visit; soft device-fingerprint hints are privacy-hostile and unreliable)
- B3 + B4 → **"absentee-member"** (system cannot detect cross-device session — cookies are browser-scoped; both look identical at the request layer: no session cookie present)
- B5, B6, B7 → distinct (B5 via session cookie; B6 via session-cookie-with-disabled-flag; B7 via session-cookie + model-access-check)

→ **5 actionable recipient states from system perspective.**

### Axis C: System Action (what system should do)

Locked after operator pruning (C5 removed — no self-serve registration planned; C7 removed — no native app planned; C8 removed — action-bridge covered by other portal-native mechanisms):

- **C1 — Show anonymous share-view** (current default for all unauthenticated)
- **C2 — Auto-redirect to member-view** (transparent route to richer view)
- **C3 — Login CTA inline** (explicit "Sign in" affordance on share-view)
- **C4 — Soft hint "you have an account, sign in"** (informational, not forced action — respects "incognito by intent" recipients)
- **C6 — Access-denied gate** (B7 case — recipient shouldn't see model at all)

### Current-state matrix (4 sender intents × 5 effective recipient states)

System reality: today, every `/share/<token>` request returns C1 (anonymous share-view) regardless of recipient state, because the share endpoint does not consult the session at all.

|                       | B1/2 anonymous | B3/4 absentee-member | B5 active session    | B6 disabled       | B7 no-access (future) |
| --------------------- | -------------- | -------------------- | -------------------- | ----------------- | --------------------- |
| **A1 friends-family** | C1 (correct)   | C1 (suboptimal)      | **C1 (the gap)**     | C1 (probably ok)  | C1 → should be C6?    |
| **A2 inter-member**   | C1 (mismatch?) | C1 (suboptimal)      | **C1 (the gap)**     | C1 (probably ok)  | C1 → should be C6?    |
| **A5 public**         | C1 (correct)   | C1 (suboptimal)      | C1 (suboptimal)      | C1 (probably ok)  | C1 → should be C6?    |
| **A6 prospect**       | C1 (correct)   | C1 (suboptimal)      | C1 (suboptimal)      | C1 (probably ok)  | C1 → should be C6?    |

### Phase 1 Key Insight (the surfacing that defines Phase 2)

**The system at link-receipt time CANNOT know sender intent A.** Token in `/share/<token>` carries only model ID, not intent. The link is intent-blind.

This forces a fork:

- **Path α (intent-blind):** System reacts purely to recipient state B. The matrix collapses to 5 cells (1-per-state). Simpler implementation; loses ability to differentiate A1 vs A2 vs A6.
- **Path β (intent-enriched):** Share-link gets intent metadata (token encodes A, OR sender picks intent at generation time, OR SHARE button is split into multiple buttons "Share with member" / "Share with friend" / etc.). System can differentiate. Conflicts with operator constraint "sender shouldn't have to know recipient state" — but sender's own intent IS knowable to sender. Question becomes: do we want to force sender to declare intent?

This dichotomy is the first non-obvious dimension surfaced by Phase 1, and is the entry point for Phase 2 (What If + Reverse Brainstorming).

### B4/C4 Detection Note

B4 (has account, logged in elsewhere) is **practically undetectable** from the share-view request alone (engineering reasoning above). Pragmatic resolution: collapse with B3 → "absentee-member", and let C3/C4 cover both via account-aware affordance shown to all unauthenticated requests. The B3↔B4 distinction only matters in the user's mental model, not in the system's decision logic.

### Phase 1 Lock-in Decision: Path α (intent-blind) only

Both paths were considered (α intent-blind, β intent-enriched). Operator (2026-05-25) decided Path β is OUT OF SCOPE for this initiative — rationale: friends-and-family user base spans tech-comfort spectrum (children, grandparents); forcing the sender to declare share-intent at link-generation time creates avoidable cognitive load and UI complexity. Single-button SHARE remains; routing decisions are made server-side based on recipient state B only.

**Implication for Sally:** UX recommendation should NOT propose multi-button SHARE, intent-picker modals, or any sender-side intent declaration. The product spec is: one SHARE button → one URL shape → server-side routing on recipient state.

## Phase 2 — What If Scenarios + Reverse Brainstorming (Path α only)

Phase 2 stress-tests the locked Path α design. All 23 scenarios were generated AI-side and operator-reviewed; operator confirmed coverage is sufficient and accepted ad-hoc handling for any new cases that emerge during implementation.

### What-If — Path α happy-path edge cases

- **α-1** Recipient on mobile, A1+B5 auto-redirect → member view may be heavier/slower than share-view on small screens. Warn before transition? Or skip redirect on mobile?
- **α-2** A2+B5 redirect lands on `/collections/list` not the specific model — **deep-link to model required** (obvious but easy to miss in implementation).
- **α-3** Multi-tab race: tab 1 = share-view as B3 (login CTA shown); user logs in tab 2 (becomes B5); tab 1 still shows stale share-view. Reactive update via service-worker / BroadcastChannel? Polling? Manual refresh hint?
- **α-4** Session expires mid-view (B5 → B3): modal? Silent downgrade to share-view? Refresh button?
- **α-5** Recipient B3 clicks "Sign in" → login form takes them to default landing (collection list), NOT back to the share-link. **Return-URL flow required** in login redirect.
- **α-6** Anonymous (B1) viewing → admin invites them mid-session → account created → but this tab still shows share-view. What now?

### What-If — Cross-path / orthogonal edges

- **x-1** Link stored in browser history → next user on shared machine clicks → wrong B-state assumed
- **x-2** Link via screenshot OCR → URL mistyped → 404 — graceful handling needed
- **x-3** Link in group chat / forum → many recipients in different B states → A5-like behavior emerges from A2-intent context (sender thought they were sending to one person, link travels)
- **x-4** Bot crawls share-links (Google indexing? Open-Graph preview bots?) — crawlers see C1 or blocked? Robots.txt? `rel="noindex"`?
- **x-5** Phishing: attacker creates look-alike share-page → user trained to "click share links" is vulnerable
- **x-6** Sender revokes link mid-view → content disappears? Modal? Soft expiry?
- **x-7** Same recipient gets 2 share-links to same model from 2 different senders → system shows what? Two parallel sessions? Single canonical view?
- **x-8** Link pasted in iframe / WebView of another app (Messenger, Facebook, Instagram) — session often isolated per-WebView → eternal B3 even when main browser has B5 (operator confirmed not blocking; handle ad-hoc when it surfaces)

### Reverse Brainstorming — "how does Path α fail most spectacularly"

- **rα-1** Auto-redirect with no breadcrumb: recipient clicks share-link → bounce to `/collections/123` → "where am I, how do I go back?" → gives up. **Mitigation:** preserve URL or add visible "you came from a shared link" affordance after redirect.
- **rα-2** Login CTA too aggressive on B3: feels like paywall → user backs out → share-link "burned" reputationally. **Mitigation:** soft hint over hard wall; never block content access.
- **rα-3** Soft hint too subtle: B3 user never notices the affordance, watches degraded view, thinks "this app is broken". **Mitigation:** account-aware affordance needs sufficient visual weight; A/B test placement.
- **rα-4** Disabled B6: redirect attempt → "account disabled" page → embarrassing to recipient who didn't know they were disabled. **Mitigation:** B6 should fall through to anonymous share-view (C1), not attempt redirect.
- **rα-5** Future B7: deny gate too aggressive → "but my friend sent it??" → sender embarrassed by an access-control mismatch they didn't know about. **Mitigation:** if B7 is implemented, recipient gets a "request access" affordance, not a flat deny.

## Phase 3 — Cross-Pollination

Reference platforms grouped by closeness-of-fit to 3d-portal's friends-and-family invitation-only model:

### Closer-fit references (small / invitation-only / personal)

- **Nextcloud (file/folder share)**: anonymous share-view by default; logged-in user with cookie sees same URL but with "Open in personal Nextcloud" affordance — does NOT auto-redirect, preserves the share URL as a bookmark.
- **Pixieset / Pic-Time (wedding photo galleries)**: share-link is THE canonical URL; "client" recipients have no concept of being logged-in. Single mode of consumption. Most-aligned with current share-view but doesn't address the member-recipient gap.
- **iCloud shared albums**: anonymous web view + native-app deep-link for logged-in Apple ID — but native-app handoff is out-of-scope per operator.

### Bigger-platform references (well-known UX patterns)

- **Google Docs**: anonymous viewer mode; if logged-in Google account, opens in member chrome (comment/edit affordances depending on permission). Detection works because cross-domain Google cookie. Pattern: **enrich-in-place**, not redirect.
- **Notion**: always-visible "Sign in" button in top-right of public pages; logged-in users see workspace chrome; logged-out users can sign in without losing the page. Pattern: **always-visible login affordance + enrich-in-place after login**.
- **Figma**: community files (public) vs private — viewer/editor based on auth + permission. Patterns: graceful "permission needed" page for B7 with "request access" CTA.
- **GitHub**: public repos visible to all; logged-in users see SAME URL but with member chrome (Star/Watch/Issue buttons). Pattern: **enrich-in-place, preserve URL as bookmark**, no auto-redirect to a different URL.
- **Twitter/X, Instagram**: aggressive login walls — explicitly anti-pattern for friends-and-family use case (creates social friction; user thinks app is hostile).
- **Spotify**: track/album URL renders content + login affordance for full features. Pattern: content-first, affordance-second.

### Extracted patterns by recipient state

| Recipient State | Cross-platform pattern (best fit) | Why |
| --- | --- | --- |
| **B1/2 anonymous** | Show content + soft "Sign in if you have an invite" affordance (no hard wall) | Aggressive walls (Twitter/Insta) drive away friends-and-family recipients. Current C1 is OK; minor addition: always-visible "Sign in" affordance for B3/4 to pick up. |
| **B3/4 absentee-member** | Always-visible "Sign in" button (Notion/GitHub style) — no detection needed | We can't detect B3/4 reliably anyway. An always-visible affordance covers B3/4 invisibly: B1/2 ignores it, B3/4 clicks it. Replaces C3 + C4 with a single C3' "always-on login affordance". |
| **B5 active session** | **Enrich-in-place** (GitHub/Nextcloud style), NOT auto-redirect | Preserves URL as bookmark, preserves back-button, less disorienting. Render the model content on `/share/<token>` URL but wrap in member-chrome (full nav, gallery navigation to other models, member actions, comment, etc.). New action **C2' "enrich-in-place"** replacing C2 "auto-redirect". |
| **B6 disabled** | Fall through to anonymous C1 (current behavior) | Avoid embarrassing "account disabled" message; recipient still gets to see the model as anonymous. Defer better handling. |
| **B7 no-access (future)** | "Request access" page (Figma/Google Docs style) | Explicit denial + actionable affordance, not silent failure. Out of scope until granular sharing exists. |

### Phase 3 key insight — C2 redefinition

The original C action set defined **C2 = auto-redirect to `/collections/<id>`**. Cross-pollination strongly suggests this is the wrong primitive — every major platform prefers **enrich-in-place** (same URL, richer chrome) over hard redirect. Replacing C2 with **C2' "enrich-in-place"** gives:

- URL stability (share-link remains the share-link; bookmark-able)
- No back-button disorientation
- Recipient can still navigate to their own collection from the enriched member-chrome
- Simpler routing (no URL rewrite, just conditional chrome render)

Similarly, the original C3 (login CTA inline) + C4 (soft hint) collapse to **C3' "always-on login affordance"** based on the Notion/GitHub pattern + the engineering reality that B3/B4 are undetectable.

### Revised action set for Sally

- **C1** Anonymous share-view (current — kept for B1/2/6)
- **C2'** Enrich-in-place with member-chrome (new — for B5)
- **C3'** Always-on login affordance on share-view (replaces old C3+C4 — for B1/2/3/4 universally)
- **C6** Request-access page (for future B7)

→ **3 distinct render modes** instead of original 5 actions. Simpler than expected.

### Revised target matrix (post-Phase-3)

|                            | B1/2 anonymous | B3/4 absentee | B5 active | B6 disabled | B7 no-access (future) |
| -------------------------- | -------------- | ------------- | --------- | ----------- | --------------------- |
| All sender intents (α-only) | C1 + C3'       | C1 + C3'      | **C2'**   | C1          | **C6**                |

Note: C1 + C3' bundled together is the same render — anonymous share-view that always includes the "Sign in" affordance. Effectively two render modes (anonymous + enriched) plus B7's future request-access page.

### B6 Disabled — operator decision

Operator (2026-05-25) selected **fall-through to C1** for B6 — disabled members see the anonymous share-view with no mention of their account state. Rationale: avoids embarrassing "account disabled" page; preserves model viewing for the recipient; avoids leaking account state to whoever else might be on the same machine. Defer richer B6 handling until disabled-account usage data exists.

## Phase 4 — Synthesis and Handoff

### Session deliverables (what Sally and `bmad-correct-course` consume)

**Two render modes + one future mode:**

1. **Anonymous share-view** (B1/2/3/4/6): current share-view chrome + new always-on "Sign in" affordance in the header.
2. **Enriched member share-view** (B5): SAME `/share/<token>` URL, but content wrapped in member-chrome (full nav, cross-model navigation, member actions). Server-side conditional render based on session cookie. NO redirect.
3. **Request-access page** (B7, future): blocked render with "ask admin for access" affordance. Out of scope until granular sharing exists.

**Explicit non-goals:**

- No multi-button SHARE (Path β killed at Phase 1).
- No sender-side intent declaration.
- No content/UX enrichment of the anonymous share-view itself beyond the "Sign in" affordance — policy 2026-05-23 ([[feedback_share_view_scope_boundary]]) stands for anonymous experience.
- No self-serve registration CTA (C5 ruled out).
- No native-app handoff (C7 ruled out).
- No action-bridge UI (C8 ruled out — handled via portal-native flows or external comm channels).

**Implementation hot-spots from Phase 2 (must-address in story specs):**

- **α-2** Deep-link to specific model when enriching B5's view (don't just wrap, route content correctly).
- **α-5** Return-URL flow in login redirect from share-view (don't drop user on default landing).
- **rα-1** Preserve URL stability — the "enrich-in-place" principle prevents this failure mode by design.
- **rα-3** Affordance visibility — "Sign in" button needs sufficient visual weight; not a footnote.

**Deferred edge cases (handle ad-hoc when they surface, per operator):**

- α-3, α-4, α-6: multi-tab race, session expiry mid-view, mid-session account creation.
- x-1 through x-8: history-leak, OCR-typed URL, group-chat propagation, bot crawling, phishing, link revocation mid-view, dual-link from two senders, WebView session isolation.

### Policy implication for `bmad-correct-course`

The share-view-terminus policy ([[feedback_share_view_scope_boundary]]) does NOT need reversal — the proposed work is **completion of the membership-path decision tree**, not enrichment of the anonymous share-view. Specifically:

- Anonymous share-view content/layout: UNTOUCHED (terminus stands).
- Anonymous share-view chrome: gets ONE new affordance ("Sign in" button). Operator should confirm this single chrome change is in-scope or out-of-scope vs the existing terminus.
- B5 enriched render: NEW work, not a share-view enrichment — it's the member-view rendering at a share URL.
- B7 future work: defer.

**Recommended amendment to memory `feedback_share_view_scope_boundary.md`:**

> Carve-out (2026-05-25): "Sign in" affordance in share-view chrome AND B5 enrich-in-place render are NOT considered share-view UX enrichment — they are membership-path completion. Anonymous share-view content (layout, gallery, description placement, STL listing, viewer behavior) remains TERMINUS for development.

### Handoff hooks

- **Next skill: `bmad-agent-ux-designer` (Sally)** — **COMPLETE 2026-05-25**. Output: `_bmad-output/ux/share-flow-membership-path-ux.md`. Sally's recommendation locked: Sign in placement (combined-with-banner, right-aligned), B5 enrich-in-place Variant γ (full canonical member view + dismissible info-bar), single-string copy ("Zaloguj się" / "Sign in"). Three operator decisions surfaced for correct-course: (1) Sign in carve-out confirmation, (2) LangToggle + ThemeToggle on share-view chrome (Sally votes amend), (3) info-bar dismissal scope (Sally picked sessionStorage).
- **Next skill: `bmad-correct-course`** — input = this document + `_bmad-output/ux/share-flow-membership-path-ux.md`. Asks: resolve Decisions 1-3 from Sally's doc; amend `feedback_share_view_scope_boundary.md` per resolved scope; create PRD / SCP for membership-path-completion initiative; sprint-plan scope (Sally estimates ~3 stories: backend resolve branch + return-URL flow, frontend conditional render + MemberShareView + info-bar, frontend chrome additions).

### Session summary (concise)

- **Generated:** 23 distinct what-if/edge/failure scenarios across one path (intent-blind / Path α) after Path β was pruned at Phase 1.
- **Surfaced 2 non-obvious design pivots:**
  1. The system has no access to sender intent at link-receipt time → routing must be recipient-state-only (Path α lock-in).
  2. Cross-platform convention strongly prefers "enrich-in-place" over auto-redirect → reframes C2 from URL rewrite to conditional chrome render.
- **Collapsed:** 5 original C actions → 3 effective render modes after engineering reality and pattern-transfer constraints.
- **Confirmed:** original share-view-terminus policy survives; new work is membership-path completion, not policy reversal.




