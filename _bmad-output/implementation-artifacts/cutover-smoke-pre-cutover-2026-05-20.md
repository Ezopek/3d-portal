# Cutover smoke baseline — 2026-05-20 (Story 10.1 T7)

**Result:** ✅ 4/4 PASS in 1s (Decision J ≤30s budget)
**Date:** 2026-05-20T14:52:42Z (UTC)
**Portal:** https://3d.ezop.ddns.net (deployed `.190`, still IP-allowlisted via nginx-180)
**Executor:** Claude Opus 4.7 (1M context), via BMAD bmad-dev-story (autonomous mode)
**Script:** `infra/scripts/cutover-smoke.sh` (Story 10.1 T1)
**STL fixture:** `infra/fixtures/cutover-test-3kb.stl` (2484 bytes, 48 triangles, sha256 `540eee5d3640fedebad1443ac5c9881c62a70ee195c9d1a7be1810e3b8d55af9`)

## Scenario table

| # | Scenario              | Expected | Actual  | Status | Timestamp (UTC)        | Request ID                                                                  |
|---|-----------------------|----------|---------|--------|------------------------|-----------------------------------------------------------------------------|
| 1 | share bypass          | 200      | 200     | PASS   | 2026-05-20T14:52:42Z   | `0350080b-a321-4a8a-afea-bee5bc7c1ada`                                      |
| 2 | agent ingestion       | 201\|200 | 200     | PASS   | 2026-05-20T14:52:42Z   | `14802518-b5eb-4ef5-9185-04b4a41bc8fe`                                      |
| 3 | member login          | 200+cookie | 200   | PASS   | 2026-05-20T14:52:42Z   | `1371d499-5e4e-4c51-91cf-ed7fb435c4a9`                                      |
| 4 | admin login + scope   | 200,200  | 200,200 | PASS   | 2026-05-20T14:52:42Z   | `4a3f0740-9e1e-4ec3-8e17-d3b9a72e7e38`                                      |

**Note on Scenario 2:** Actual=200 (HTTP 200) on this run reflects the sha256-dedup
path of `POST /api/admin/models/{id}/files` — the same STL fixture was already
uploaded on the prior smoke run (and on its initial author-time smoke). Per the
script header dispatch + Story 10.1 spec reconciliation, both 200 and 201 are
PASS for this scenario.

## Fixtures live at baseline

| Fixture | Identity / value | Source |
|---|---|---|
| Test-member account | `cutover-smoke@portal.ezop.ddns.net` (user_id `79d8d412-a4c3-4b46-aa01-347f922a6c52`, role=member, totp_enabled_at IS NULL) | Story 10.1 T4 — invite generated 2026-05-20T14:45:37Z, ttl_preset=SEVEN_DAYS, registered same session |
| Test model (Scenario 2 target) | `beeaf137-6696-498c-b4d9-d9d33ba28c39` | Pre-existing catalog model (3D Printable Switch Replacement) |
| Initial share-token | `eiLg49EcjPgZHGAtQKjTppVzKsVmI3xf` (expires 2026-05-21T14:48:28.844703Z) | Story 10.1 T5 — created via member-authenticated `POST /api/admin/share`, will be rotated hourly by `cutover-share-token-refresh.sh` |
| Agent service account | `agent@portal.example.com` (user_id `445c1709-1d3a-439c-a812-a817601e264a`, role=agent, totp_enabled_at IS NULL) | Pre-existing on `.190`; AGENT_PASSWORD rotated via DB-direct surgery in api container per Decision L §1741 + NFR5-INT-1 bootstrap-script-managed contract |

## Wall-clock budget

| Metric | Value | Budget | Status |
|---|---|---|---|
| Total elapsed | 1 s | ≤30s (Decision J) | ✅ 29s headroom |
| Per-scenario `curl --max-time` cap | 7 s | — | not exceeded on any call |

## Rate-limit observation

Two back-to-back smoke runs at 14:49:39 + 14:49:46 (gap = 7s) trip Story 7.5
AC-4 (5-login-failures-per-60s sliding window per IP). The second run failed
Scenario 4 with HTTP 429 on admin login — NOT a regression; the rate-limit is
the documented contract. Operators executing the Decision K rollback cycle
MUST wait ≥60s between consecutive smoke runs from the same source IP. This
constraint is documented inline in `cutover-smoke.sh`'s header. Story 10.3
runbook must surface the gap explicitly in the rollback-drill sequence.

## Story 10.3 consumption pointer

Story 10.3 reuses this baseline as the pre-cutover reference shape. The
artifact slot for the cutover-day smoke is
`_bmad-output/implementation-artifacts/cutover-smoke-<cutover-date>.md` — a
DIFFERENT file, written by Story 10.3's artifact path (not this script).
