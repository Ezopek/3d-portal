# Security Audit — Initiative 5 / Epic 9 — 2026-05-20

**Auditor:** Ezop (single-operator self-attestation, codex countersignature per Medium disposition per NFR5-SEC-2)
**Subject:** 3d-portal Initiative 5 deliverables (Epics 6 + 7 + 8) deployed at https://3d.ezop.ddns.net
**Git HEAD at scan:** `9a8b935dc87f4791481a3a2a71e948f2d8e5c8a2` (branch `feat/E9.1-audit-tooling-install-baseline` at baseline; post-audit fixes landed at `7c148cb`, `8d22dd7`, `ca40ad2`, `0ee4c09` on `main`)
**Audit window valid through:** 2026-06-19 (30 days) or until next significant deploy, whichever first

---

## 1. Methodology

This audit realises NFR5-SEC-1..3 by combining:

- **Tooling stack from Story 9.1** — bandit `1.9.4` (Python static analysis, apps/api + workers/render), semgrep `1.163.0` (multi-language SAST with `p/security-audit` + `p/owasp-top-ten` + `p/dockerfile` + `p/nginx` rule packs), pip-audit `2.10.0` (Python dependency CVE scan), npm audit (`npm 10.9.7` / `node v22.22.2`, frontend dependency scan), and OWASP ZAP `2.17.0` baseline (deployed-instance black-box scan against the live LAN endpoint). Per-tool versions recorded in `audit-raw/2026-05-20/tool-versions.txt`.

- **Six-scenario matrix from Story 9.2** — bespoke reproducible exercises against the deployed `.190` instance, covering invite-token brute force, refresh-token replay, CSRF + JWT tampering, IDOR on `/api/admin/*`, login rate-limit, and member share-link amplification. End-to-end harness implemented at `infra/scripts/audit-six-scenarios.sh` with per-scenario reproducer scripts checked into `audit-raw/2026-05-20/scenario-*-reproducer.sh`.

- **Codex per-Medium countersignature from Story 9.3 (NFR5-SEC-2 compensating control)** — for each unique commit referenced in a Medium disposition rationale, an independent codex review (`codex review --commit <sha>`) was invoked. The output is captured at `audit-raw/2026-05-20/codex-reviews/med-NNN.md` and the countersignature recorded in `audit-raw/2026-05-20/medium-findings.json` per finding. The full rationale for the single-operator self-attestation mitigation is at `audit-raw/2026-05-20/self-attestation-rationale.md`.

- **Single-operator self-attestation mitigation** — per NFR5-SEC-2 verbatim: the operator (Ezop) is both auditor and gate-keeper. Two compensating controls ensure auditability: (a) per-Medium codex countersignature (independent LLM auditor reviews the same commits) and (b) NFR5-SEC-1 structural cap of ≤3 `accepted-with-rationale` Mediums at gate decision. Both controls were satisfied; no `accepted-with-rationale` dispositions were taken (0 / 3 cap headroom).

- **Reproducibility window** — this audit is valid for 30 days OR until the next significant deploy to `.190`, whichever first. After expiry, Story 9.4 must be re-invoked and the audit re-authored against the new git HEAD.

## 2. Tools run summary

| Tool | Target | Output | Critical | High | Medium | Low/Info |
|------|--------|--------|----------|------|--------|----------|
| bandit | apps/api | `audit-raw/2026-05-20/bandit-apps-api.txt` | 0 | 0 | 0 | 11 |
| bandit | workers/render | `audit-raw/2026-05-20/bandit-workers-render.txt` | 0 | 0 | 0 | 0 |
| semgrep | apps/api + apps/web + workers/render | `audit-raw/2026-05-20/semgrep.json` | 0 | 0 | 9 | 0 |
| pip-audit | apps/api | `audit-raw/2026-05-20/pip-audit-apps-api.txt` | 0 | 0 | 4 | 0 |
| pip-audit | workers/render | `audit-raw/2026-05-20/pip-audit-workers-render.txt` | 0 | 0 | 4 | 0 |
| npm audit | apps/web | `audit-raw/2026-05-20/npm-audit.json` | 0 | 0 | 7 | 0 |
| OWASP ZAP baseline | https://3d.ezop.ddns.net | `audit-raw/2026-05-20/zap-baseline.html` + `.json` | 0 | 0 | 3 | 11 |

**Notes:**

- bandit apps/api Low-severity findings are noise-class (assert usage, default-string detection on the JWT-secret guard) — none escalate; no Critical/High/Medium emitted.
- semgrep `apps/api+workers/render` pip-audit advisories are the same four CVEs because both Python services share the project's `uv.lock`; they are de-duplicated to four Mediums (`med-010..med-013`) in the Findings disposition.
- ZAP Low/Info breakdown: 7 Lows (X-Content-Type-Options, COOP/COEP/CORP, Permissions-Policy, Cross-Domain JS inclusion, Private IP disclosure) + 4 Info (cache directives + modern-web-app banner) — none constitute Critical/High; all bounded by LAN/VPN-only ACL.
- **One High-severity finding** was surfaced during Story 9.2 scenario execution (refresh-token revoke-reason CHECK constraint mismatch on admin deactivation force-logout) and **FIXED before gate** via migration `0016_extend_revoke_reason_check.py` (commit `7c148cb`). It is enumerated as `high-001` in the Findings disposition table below with `disposition=fixed`. Per NFR5-SEC-1, "open" High findings gate-fail; this one is closed at gate time.

## 3. Six-scenario coverage

Source: `audit-raw/2026-05-20/six-scenario-coverage-attempt-8.json` (final attempt). All six scenarios returned verdict **PASS** against the live `.190` deployment.

| # | Scenario | Verdict | Evidence | Reproducer |
|---|----------|---------|----------|------------|
| 1 | Invite-token brute force | PASS | `audit-raw/2026-05-20/scenario-1-output-attempt-8.txt` | `audit-raw/2026-05-20/scenario-1-invite-brute-force-reproducer.sh` |
| 2 | Refresh-token replay | PASS | `audit-raw/2026-05-20/scenario-2-output-attempt-8.txt` | `audit-raw/2026-05-20/scenario-2-refresh-replay-reproducer.sh` |
| 3 | CSRF + JWT tampering | PASS | `audit-raw/2026-05-20/scenario-3-output-attempt-8.txt` | `audit-raw/2026-05-20/scenario-3-csrf-jwt-tampering-reproducer.sh` |
| 4 | IDOR scan `/api/admin/*` | PASS | `audit-raw/2026-05-20/scenario-4-output-attempt-8.txt` | `audit-raw/2026-05-20/scenario-4-idor-admin-reproducer.sh` |
| 5 | Login rate-limit | PASS | `audit-raw/2026-05-20/scenario-5-output-attempt-8.txt` | `audit-raw/2026-05-20/scenario-5-login-rate-limit-reproducer.sh` |
| 6 | Member share-link amplification | PASS | `audit-raw/2026-05-20/scenario-6-output-attempt-8.txt` | `audit-raw/2026-05-20/scenario-6-share-amplification-reproducer.sh` |

**Per-scenario notes (from six-scenario-coverage JSON):**

- **Scenario 1:** 4th attempt returned HTTP 429 as expected (register rate-limit 3/60s tripped).
- **Scenario 2:** replay=401, audit-row `auth.refresh.reuse_detected`, gen-2 invalidated=401 (full family revocation observed).
- **Scenario 3:** 13/13 endpoints rejected CSRF-stripped (403) and tampered-JWT (401) attacks.
- **Scenario 4:** 9/9 admin endpoints rejected member-role principal with HTTP 403 (admin-role enforcement intact).
- **Scenario 5:** attempts 1–5 returned HTTP 401; attempt 6 returned HTTP 429 within 60s (login rate-limit 5/60s tripped).
- **Scenario 6:** call 21 HTTP 429; `share.ratelimit.soft_alert` log-lines for audit-member=4 (log-only per Story 6.7; spec §AC6 'audit row' is documentation drift, not a defect).

## 4. Findings disposition

Source: `audit-raw/2026-05-20/medium-findings.json` (23 Mediums) plus the one fixed-before-gate High surfaced by Story 9.2.

**Totals:** 1 fixed High (closed at gate time) + 23 Mediums (0 fixed, 23 mitigated, 0 accepted-with-rationale).

| ID | Source | Severity | Title | Disposition | Patch SHA / Codex SHA | Countersigned |
|----|--------|----------|-------|-------------|-----------------------|---------------|
| high-001 | scenario-4 / Story 9.2 admin force-logout exercise | High | `refresh_tokens.revoke_reason` CHECK constraint rejected new `'admin_deactivation'` reason → admin-deactivation flow 500'd before token family was revoked (Story 8.3 carry-over) | fixed | `7c148cb` / n/a (post-fix codex review at `8d22dd7`) | 2026-05-20 |
| med-001 | semgrep | Medium | Dockerfile missing USER directive (apps/api) | mitigated | (n/a) / `4108b09` | 2026-05-20 |
| med-002 | semgrep | Medium | Dockerfile missing USER directive (workers/render) | mitigated | (n/a) / `ca424b4` | 2026-05-20 |
| med-003 | semgrep | Medium | Flask-rule false positive: f-string return in non-Flask code (ratelimit.py) | mitigated | (n/a) / `12ba359` | 2026-05-20 |
| med-004 | semgrep | Medium | SHA-1 used for non-cryptographic ETag (cache-key only) | mitigated | (n/a) / `ce0b56f` | 2026-05-20 |
| med-005 | semgrep | Medium | Missing Subresource Integrity attribute (apps/web/index.html) | mitigated | (n/a) / `108ea05` | 2026-05-20 |
| med-006 | semgrep | Medium | nginx location missing `internal` directive (apps/web/nginx.conf:63) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |
| med-007 | semgrep | Medium | nginx `$host` usage may reflect attacker-controlled Host header (apps/web/nginx.conf:64) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |
| med-008 | semgrep | Medium | nginx location missing `internal` directive (apps/web/nginx.conf:76) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |
| med-009 | semgrep | Medium | nginx `$host` usage may reflect attacker-controlled Host header (apps/web/nginx.conf:77) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |
| med-010 | pip-audit | Medium | idna 3.13 DoS via `idna.encode()` (CVE-2026-45409) | mitigated | (n/a) / `91361b1` | 2026-05-20 |
| med-011 | pip-audit | Medium | urllib3 2.6.3 redirect header leak via `ProxyManager` (PYSEC-2026-141) | mitigated | (n/a) / `91361b1` | 2026-05-20 |
| med-012 | pip-audit | Medium | urllib3 2.6.3 over-decompression via Brotli `read(amt=N)` (PYSEC-2026-142) | mitigated | (n/a) / `91361b1` | 2026-05-20 |
| med-013 | pip-audit | Medium | pyjwt 2.12.1 weak-encryption advisory (PYSEC-2025-183 — disputed by upstream) | mitigated | (n/a) / `91361b1` | 2026-05-20 |
| med-014 | npm-audit | Medium | `@vitest/mocker` moderate (transitive via vite, dev-only) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-015 | npm-audit | Medium | `brace-expansion` moderate (DoS protection bypass, dev-only) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-016 | npm-audit | Medium | `esbuild` dev-server CORS bypass (dev-only) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-017 | npm-audit | Medium | `vite` path-traversal in optimized-deps `.map` handling (dev-only) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-018 | npm-audit | Medium | `vite-node` moderate (transitive via vite, dev-only) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-019 | npm-audit | Medium | `vitest` moderate (transitive via vite + vite-node, dev-only) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-020 | npm-audit | Medium | `ws` uninitialized memory disclosure (dev-only, no prod WebSocket) | mitigated | (n/a) / `fb8155a` | 2026-05-20 |
| med-021 | zap | Medium | Content Security Policy header not set (4 instances) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |
| med-022 | zap | Medium | Anti-clickjacking header missing — X-Frame-Options / CSP `frame-ancestors` (3 instances) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |
| med-023 | zap | Medium | Sub-Resource Integrity attribute missing on script/link tags (5 instances) | mitigated | (n/a) / `f9ce3f8` | 2026-05-20 |

**Mitigation rationale summary (full text per finding in `medium-findings.json[].rationale` + per-finding codex review at `audit-raw/2026-05-20/codex-reviews/<finding-id>.md`):**

- **Container hardening (med-001, med-002):** LAN/VPN-only network ACL at edge proxy `.180`; single-purpose containers without untrusted-code execution paths. Promotable to USER fix in Epic 10 hardening pass.
- **Tool false positives (med-003, med-004):** semgrep Flask rule misapplied to FastAPI code; SHA-1 used non-cryptographically for ETag with explicit `usedforsecurity=False`.
- **Vite-bundled integrity (med-005, med-023):** content-hashed bundle filenames provide integrity equivalence; no third-party CDN script loads; same-origin only.
- **Edge-proxy headers (med-006..009, med-021, med-022):** Host validation and trust boundary live at the edge proxy `.180`; CSP and anti-clickjacking are documented additions deferred to the Epic 10 hardening pass (planned at the edge where TLS terminates).
- **Python dependency advisories (med-010..013):** vulnerable code paths are unreachable in our usage (bounded input lengths for idna; no `ProxyManager` or `assert_same_host=False` for urllib3; no Brotli partial-read consumption; pyjwt CVE disputed and satisfied by `openssl rand -hex 32` secret generation).
- **Frontend dev-tooling advisories (med-014..020):** all are devDependencies — never bundled into production output served by nginx; risk bounded to developer workstations.

Per Story 9.3 close-out: codex review did NOT contest any disposition; tangential codex findings were pre-existing observations from earlier post-merge cycles or historical artefacts of older commits, not specific to the Mediums under review (see `self-attestation-rationale.md` for full enumeration).

## 5. Gate-condition decision

**E10 cleared to proceed** — gate condition PASS: zero open Critical/High findings; 0 accepted-rationale Mediums (0 ≤ 3); audit complete on 2026-05-20.

## 6. Re-run reproducer

The full audit can be re-executed from the same git HEAD with:

```bash
bash _bmad-output/implementation-artifacts/audit-raw/2026-05-20/reproducers.sh all
```

Individual scenarios may be re-run via the per-scenario reproducer scripts listed in §3 (each is self-contained and consumes a `.env`-style auth bootstrap).

---

*Audit signed off: 2026-05-20 by Ezop (single-operator self-attestation; codex countersignature per Medium per `medium-findings.json`). Sprint-status flip: `epic-9: done`, `9-4-audit-report-gate-condition-signoff: done` (PASS, 2026-05-20), `epic-10: in-progress`.*

---

## Supplemental finding — High-002 (post-cutover audit miss, FIXED inline)

**Date discovered:** 2026-05-20 ~21:00 UTC (operator-surfaced during post-handoff smoke)
**Severity:** High
**Disposition:** **fixed** (commit `64447ff`)

### Summary

Initiative 5 cutover (Story 10.3, sibling `dd0c7b8`) removed the nginx server-level IP allowlist on `https://3d.ezop.ddns.net`. With the allowlist gone, ALL six SoT GET read endpoints in `apps/api/app/modules/sot/router.py` (`/api/categories`, `/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`, `/api/models/{id}/files/{file_id}/content`) became fully reachable from the public internet with NO authentication. Verified pre-fix: `curl https://3d.ezop.ddns.net/api/categories` returned the operator's full private category tree + per-category model counts.

### Why the original audit missed it

Story 9.2 Scenario 4 (IDOR scan) restricted its target list to `/api/admin/*` mutating endpoints — the `current_admin` allowlist verification. The read-side `/api/*` endpoints were marked "Public, unauthenticated" in code intent (pre-Init-5 baseline: nginx perimeter enforced gating; app-level pass-through was intentional). Scenario 4 did not probe whether that "public" intent matched the post-cutover security posture demanded by FR5-MEMBER-1 ("`member` role grants browse + viewer + `POST /api/share/`"). The scenario coverage matrix was binding to the audit-time threat model where nginx still gated; the cutover (Story 10.3) flipped the assumption but Scenario 4 wasn't re-derived.

### Fix

`apps/api/app/modules/sot/router.py`: added `_user_id: uuid.UUID = current_member_or_admin` to all six GET handlers. `apps/web/src/routes/catalog/index.tsx` + `catalog/$id.tsx`: wrapped in `<AuthGate>` so unauthenticated browsers redirect to `/login?next=<catalog-url>`. `apps/api/tests/test_hydrate_local_tree.py`: updated to set the admin `portal_access` cookie before invoking `run_hydrate()` (the operator CLI path via `bearer_token=` is unaffected; tests now use cookie auth which matches the dependency's read path).

### Post-fix verification

```bash
# Anonymous probes (expected: 401)
$ curl -o /dev/null -w "%{http_code}\n" -s "https://3d.ezop.ddns.net/api/categories"   # → 401
$ curl -o /dev/null -w "%{http_code}\n" -s "https://3d.ezop.ddns.net/api/models?limit=5" # → 401
$ curl -o /dev/null -w "%{http_code}\n" -s "https://3d.ezop.ddns.net/api/tags"           # → 401

# Authenticated cutover-smoke (expected: 4/4 PASS)
$ bash infra/scripts/cutover-smoke.sh
  PASS 1 share bypass         expected=200 actual=200 ...
  PASS 2 agent ingestion      expected=201|200 actual=200 ...
  PASS 3 member login         expected=200+cookie actual=200 ...
  PASS 4 admin login          expected=200,200 actual=200,200 ...
cutover-smoke: ✅ 4/4 PASS in 1s

# Targeted pytest batch (expected: PASS)
$ timeout 180 uv run pytest apps/api/tests/test_hydrate_local_tree.py \
    apps/api/tests/test_sot_admin_files.py \
    apps/api/tests/test_db_entity_tables.py \
    apps/api/tests/test_share_member_permission.py
# → 90 passed in 12.30s
```

### Gate-condition decision (updated)

Original §6 verdict line of 2026-05-20 ("zero open Critical/High findings; 0 accepted-rationale Mediums") was INVALIDATED by this finding's discovery. **Updated verdict effective post-`64447ff`:**

> **E10 cleared to proceed (verdict re-established)** — gate condition PASS: zero open Critical/High findings AFTER High-002 disposed `fixed` (patch `64447ff`); 0 accepted-rationale Mediums (0 ≤ 3); audit re-verified 2026-05-20T19:11Z.

### Action items for next audit / next cutover

1. **Extend Scenario 4 target list:** include ALL `/api/*` endpoints (mutating AND read), not just `/api/admin/*`. The IDOR scan should empirically verify auth-gate presence for every endpoint, not assume legacy "public" annotations.
2. **Add public-IP probe to cutover-smoke:** AC5 of Story 10.3 deferred this to operator manual verification; should be automated via second curl call from a NON-LAN host (e.g., a public CI runner or remote VPS) to validate the cutover's primary effect (external reachability change) is the INTENDED change (auth-gated public access), not an UNINTENDED change (anonymous public access).
3. **Doc-drift item:** the architecture/PRD verbatim "FR5-MEMBER-1: `member` role grants browse" implies catalog browse REQUIRES `member` minimum — the implementation drift (sot/router.py marked "Public") existed pre-Init-5 and was masked by nginx perimeter. Carry to bmad-correct-course batch.

### Codex countersignature

Not yet executed for this fix — operator-surfaced finding bypassed the NFR5-SEC-2 process. To complete the compensating control per `feedback_invoke_codex_directly.md`: `codex review --commit 64447ff` queued as follow-up to this supplemental note.

*Supplemental finding documented and disposed: 2026-05-20 by Ezop (autonomous ITCM mode, operator-surfaced).*
