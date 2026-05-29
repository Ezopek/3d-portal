---
title: 'Story 23.3 — Share per-token rate-limit middleware (TB-026 sub#6 per-token)'
type: 'security-hardening'
status: 'ready-for-dev'
story_id: '23.3'
epic: 'E23 — Share-View Security Hardening'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-026 sub#6 per-token addition'
fr_ref: 'FR16-RATELIMIT-PER-TOKEN-1'
architectural_anchor: 'Decision Y'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.5 per [[feedback_codex_model_routing]] security class)'
estimated_effort: '1.5-2 h: NEW key_fn + Settings fields + middleware mount + tests + pen-test plan'
created: '2026-05-24'
---

# Story 23.3 — Share per-token rate-limit middleware (TB-026 sub#6 per-token addition)

Status: ready-for-dev

## Story

As a defender against IP-pool attackers (botnets) that distribute scraped share-token requests across many IPs to defeat the existing per-(token, IP) cap,
I want an additional app-level rate-limit middleware that caps per-share-token request count regardless of source IP,
so that even a million-IP botnet wielding a single scraped token cannot exceed 60 req/min total (closes TB-026 sub#6 per-token operator-decision addition; layered defense on top of Init 12 Story 19.1 per-(token, IP) middleware).

## Acceptance Criteria

1. **AC1 — NEW per-token key_fn `share_anon_per_token_ratelimit_key`** in `apps/api/app/core/auth/ratelimit.py`. Identical token-hash extraction logic to existing `share_anon_ratelimit_key` (Story 19.1) BUT returns `f"token:{token_hash}"` WITHOUT the IP suffix. Result: all requests bearing the SAME share token share one bucket regardless of source IP.

2. **AC2 — NEW retry_after_fn `share_anon_per_token_retry_after_seconds`** in same file. Reads `get_settings().ratelimit_share_per_token_window_seconds` at call time (mirrors existing pattern at lines 215-221).

3. **AC3 — NEW Settings fields** in `apps/api/app/core/config.py`:
   - `ratelimit_share_per_token_window_seconds: int = 60` (default 60s sliding window)
   - `ratelimit_share_per_token_threshold: int = 60` (default 60 req/min/token per operator AskUserQuestion 2026-05-24)
   - `ratelimit_share_per_token_soft_alert_threshold: int | None = None` (optional alert threshold; default None = no soft alert)
   - Field validators: thresholds ge=1 le=100000; window seconds ge=10 le=3600. Misconfig → ValidationError at startup-config-load (matches Init 12 Story 19.1 precedent).

4. **AC4 — NEW RateLimitMiddleware instance mounted in `apps/api/app/main.py`** (5th instance, AFTER the existing 4 per Init 12 Story 19.1):
   - `scope="share_anon_per_token"`
   - `key_fn=share_anon_per_token_ratelimit_key`
   - `window_seconds=get_settings().ratelimit_share_per_token_window_seconds`
   - `threshold=get_settings().ratelimit_share_per_token_threshold`
   - `soft_alert_threshold=get_settings().ratelimit_share_per_token_soft_alert_threshold`
   - `retry_after_seconds_fn=share_anon_per_token_retry_after_seconds`

5. **AC5 — Composable with Story 19.1 per-(token, IP) middleware.** Both middlewares fire on `/api/share/{token}/*` requests. EITHER overage returns 429 (not BOTH required). Order: per-(token, IP) outer (cheaper key, more common abuse vector); per-token inner. Test fixture exercises both legs independently:
   - Per-(token, IP) overage from single IP: 429 surfaces from Story 19.1 middleware (verifiable via existing test).
   - Per-token overage from distributed IPs (mock multiple X-Forwarded-For values): 429 surfaces from NEW Story 23.3 middleware.
   - Both clean: 200 response (normal traffic).

6. **AC6 — env wiring.** `infra/env.example` (and `infra/docker-compose.yml` if existing share_anon env keys are listed there) get 3 new commented annotations:
   - `# RATELIMIT_SHARE_PER_TOKEN_WINDOW_SECONDS=60`
   - `# RATELIMIT_SHARE_PER_TOKEN_THRESHOLD=60`
   - `# RATELIMIT_SHARE_PER_TOKEN_SOFT_ALERT_THRESHOLD=  # optional, default unset`

7. **AC7 — Threat-vector enumeration in spec (NFR16-SECURITY-1 per [[feedback_security_vector_enumeration]]).** This section in spec Dev Notes covers:
   - Share-token leak vectors (referrer header on linked content, screenshot share, copy-paste-then-redistribute, log leakage).
   - IP-pool attacker scenarios (botnet defeats per-IP cap → per-token cap catches).
   - Retry-After backoff exploitation (attacker bounded by window cap regardless of compliance).
   - Share-scoped DDoS multiplier (without per-token cap: M IPs × N tokens × 60 req/min/IP = vast surface; with: N tokens × 60 req/min total).
   - Soft-alert threshold use case (operator-tuned early warning at e.g. 30 req/min/token → log to GlitchTip for proactive monitoring).

8. **AC8 — NEW pytest** `apps/api/tests/test_ratelimit_share_per_token.py` mirroring `test_ratelimit_share_anon.py` shape:
   - Per-token cap from N IPs (parametrize 2-3 IPs) → assert 429 at threshold.
   - Per-token cap distinct from per-(token, IP) cap (set thresholds such that per-token < per-(token, IP); verify per-token fires first).
   - Per-token cap composability with per-(token, IP): both clean, only per-token overages, only per-(token, IP) overages.
   - Soft-alert threshold log emission (if threshold set).
   - Retry-After header matches `ratelimit_share_per_token_window_seconds`.

9. **AC9 — Backend pytest 870+/870+ PASS 3× consecutive deterministic.** Plus ~8-12 new tests in `test_ratelimit_share_per_token.py` → expect 878-882 PASS.

10. **AC10 — Ruff + alembic check clean.** No schema change (Redis-only). `alembic check` "No new upgrade operations".

11. **AC11 — Codex review CLEAN (gpt-5.5 security class).** Per [[feedback_codex_model_routing]]. Round-2 fix-up acceptable; round-3+ surfaces as new TB.

12. **AC12 — Pen-test plan documented for operator follow-up.** Story 23.3 spec includes a paste-ready pen-test scenario from `ezop-kbk.ddns.net` per [[reference_external_test_source]]:
    ```bash
    # From ezop-kbk.ddns.net (separate LAN, public-internet egress).
    # Step 1: Generate share token via authenticated dev session (operator).
    # Step 2: Loop curl from ezop-kbk with single IP — should 429 at ~60.
    # Step 3: Loop curl with rotating User-Agent (still same IP source) —
    #         should 429 at ~60 (per-token cap catches).
    # Step 4: Burst-curl normal (under threshold) — should succeed.
    for i in {1..80}; do
      ssh ezop-kbk.ddns.net "curl -s -o /dev/null -w '%{http_code}\\n' \
        https://3d.ezop.ddns.net/api/share/<token>/files"
    done | sort | uniq -c
    # Expected: ~60x 200, ~20x 429
    ```
    Operator executes post-deploy; documents result in commit body OR retrospective.

## Tasks / Subtasks

- [ ] **T1 — Ratelimit key + retry_after functions** (AC: #1, #2)
  - [ ] T1.1 — Add `share_anon_per_token_ratelimit_key(request)` to `ratelimit.py` (mirror existing `share_anon_ratelimit_key` shape; drop the IP suffix).
  - [ ] T1.2 — Add `share_anon_per_token_retry_after_seconds()` to same file.
  - [ ] T1.3 — Inline docstrings citing Story 23.3 / Decision Y / FR16-RATELIMIT-PER-TOKEN-1.

- [ ] **T2 — Settings fields** (AC: #3)
  - [ ] T2.1 — Add 3 new fields to `Settings` in `config.py` with field_validators.
  - [ ] T2.2 — Default values 60/60/None per operator decision.

- [ ] **T3 — Middleware mount** (AC: #4)
  - [ ] T3.1 — Import new key_fn + retry_after_fn in `main.py`.
  - [ ] T3.2 — Add 5th RateLimitMiddleware instance with `scope="share_anon_per_token"`.
  - [ ] T3.3 — Verify ordering: per-(token, IP) outer (Story 19.1), per-token inner (this story).

- [ ] **T4 — env wiring** (AC: #6)
  - [ ] T4.1 — `infra/env.example` adds 3 commented entries.
  - [ ] T4.2 — `infra/docker-compose.yml` adds 3 env keys if pattern matches Story 19.1 + 57faba1 fix-up.

- [ ] **T5 — Tests** (AC: #5, #8, #9)
  - [ ] T5.1 — NEW `apps/api/tests/test_ratelimit_share_per_token.py` mirroring `test_ratelimit_share_anon.py`.
  - [ ] T5.2 — Pytest 3× consecutive determinism gate.

- [ ] **T6 — Pre-merge gates** (AC: #9, #10)
  - [ ] T6.1 — ruff check + format clean.
  - [ ] T6.2 — alembic check "No new upgrade operations".
  - [ ] T6.3 — Full pytest 3× consecutive (NFR16-DETERMINISM-1).

- [ ] **T7 — Commit + Codex review + auto-deploy** (AC: #11)
  - [ ] T7.1 — Commit: `feat(share): per-token rate-limit middleware (Story 23.3, TB-026)`.
  - [ ] T7.2 — ff-merge to main.
  - [ ] T7.3 — `codex review --commit <SHA>` (default gpt-5.5 security class).
  - [ ] T7.4 — Round-2 fix-up if P1/P2.
  - [ ] T7.5 — `infra/scripts/deploy.sh`.
  - [ ] T7.6 — Sprint-status flip + TB-026 sub#6 status update.

## Dev Notes

### Existing pattern (Init 12 Story 19.1 — already shipped)

`apps/api/app/core/auth/ratelimit.py:167-205` — `share_anon_ratelimit_key(request)` returns `f"token:{token_hash}:ip:{client_ip}"`. Sliding-window via `RateLimitMiddleware` class (lines 224+). Mounted in `main.py:165-172` as 5th-or-Nth middleware.

Story 23.3 ADDS a parallel key function (drop IP) + parallel middleware mount. Existing per-(token, IP) middleware stays untouched.

### Threat-vector enumeration (NFR16-SECURITY-1)

Per [[feedback_security_vector_enumeration]] — enumerate cookie-sending vectors, auth-state-consultation points, browser-default-credentials behaviors:

**1. Share-token leak vectors.**
- Referrer header on linked content (browser sends `Referer: https://3d.ezop.ddns.net/share/<token>` to embedded image sources, third-party CDNs, etc — mitigated by NFR10-SHARE-SECURITY-1 + anonymous viewer fetching all assets via /api/share/<token> paths which stay same-origin).
- Screenshot share (recipient screenshots URL bar → token leaks visually).
- Copy-paste then redistribute (recipient pastes link to a chat → others use it).
- Log leakage (token in nginx access logs, GlitchTip URL captures).
- All these defeat the existing per-IP cap (attacker uses fresh IP pool).

**2. IP-pool attacker scenarios.**
Without per-token cap: M IPs (botnet of 1000) × per-IP cap 60 req/min = 60,000 req/min/token from one scraped token. Throughput attack: 60k req/min × 200 KB/req gallery tier = 12 GB/min outbound traffic per leaked token.

With per-token cap (60 req/min/token regardless of IP count): same scenario capped at 60 × 200 KB = 12 MB/min/token. 1000× reduction.

**3. Retry-After backoff exploitation.**
Attacker that respects `Retry-After: 60` header still bounded by window — they wait 60s then send another 60 reqs (1 req/sec sustained). Attacker that IGNORES Retry-After hits 429 storm — no further resource consumption (Redis ZADD cost is sub-millisecond; nginx response cost ~negligible). Trade-off: log volume might surge in 429 storm, monitored via soft-alert threshold.

**4. Share-scoped DDoS multiplier.**
N tokens leaked × per-token-cap 60 req/min = N × 60 req/min/operator-config attacker surface. Operator can revoke tokens to mitigate (DELETE /api/admin/share/<token> existing endpoint).

**5. Soft-alert threshold use case.**
`ratelimit_share_per_token_soft_alert_threshold = 30` → when a token hits 30 req/min sustained (half the hard cap), log structured WARNING to `app.share.ratelimit` logger (GlitchTip-visible per NFR5-OBS-1). Operator gets proactive alert without firing 429s. Default disabled (None) — operator opts in.

**6. Compose-with-per-IP threat model.**
Per-IP cap catches casual abuse (one IP exceeds threshold). Per-token cap catches sophisticated multi-IP scraping. Layered: an attacker must satisfy BOTH constraints. Trade-off: legitimate recipient sharing token across family devices (mom's phone + dad's tablet + kid's laptop on same WiFi → same IP, but 3 different sessions) gets BOTH caps but is far below either threshold (~10 req/session × 3 = 30, well under 60).

### Files to touch

**MODIFIED (4):**
- `apps/api/app/core/auth/ratelimit.py` — +2 new functions (key_fn + retry_after_fn)
- `apps/api/app/core/config.py` — +3 new Settings fields
- `apps/api/app/main.py` — +1 new RateLimitMiddleware instance (5th)
- `infra/env.example` — +3 commented entries
- `infra/docker-compose.yml` — +3 env keys if matching Story 19.1 pattern

**NEW (1):**
- `apps/api/tests/test_ratelimit_share_per_token.py` — ~200-300 LOC mirroring `test_ratelimit_share_anon.py`

**Diff stats expected:**
- ~50-80 LOC modified across 4-5 files
- ~250 LOC new test file
- Net: ~+300 LOC

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Ruff check | `cd apps/api && uv run ruff check app/core/auth/ratelimit.py app/core/config.py app/main.py tests/test_ratelimit_share_per_token.py` | Clean |
| Ruff format | `cd apps/api && uv run ruff format --check ...` | Clean |
| Alembic check | `cd apps/api && uv run alembic check` | "No new upgrade operations" |
| Pytest × 3 | `cd apps/api && timeout 600 uv run pytest -q tests/` | 878-882 PASS deterministic |
| Codex review | `codex review --commit <SHA>` (gpt-5.5 security class) | CLEAN OR fix-up cycle |
| Pen-test (operator post-deploy) | `ssh ezop-kbk.ddns.net "curl ... 80 times"` | ~60×200 + ~20×429 |

## References

- [Init 16 SCP §4.2 Story 23.3](sprint-change-proposal-2026-05-24-init16.md#42-epic-e23--share-view-security-hardening)
- [architecture.md § Decision Y](../planning-artifacts/architecture.md#decision-y--per-token-rate-limit-middleware-epic-23--fr16-ratelimit-per-token-1)
- [prd.md § FR16-RATELIMIT-PER-TOKEN-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep)
- [triage-backlog.md § TB-026 sub#6](../triage-backlog.md)
- Init 12 Story 19.1 commits: `2232b77` (primary middleware) + `57faba1` (compose env fix-up).
- Init 12 Story 19.1 spec / tests at `apps/api/tests/test_ratelimit_share_anon.py` — mirror template.
- Memory: [[feedback_codex_model_routing]], [[feedback_security_vector_enumeration]], [[reference_external_test_source]], [[feedback_pytest_timeout]], [[feedback_pre_merge_gate_checklist]].

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
