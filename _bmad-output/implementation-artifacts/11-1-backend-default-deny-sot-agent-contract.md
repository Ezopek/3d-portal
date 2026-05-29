---
story_id: "11.1"
title: "Backend default-deny gating on SoT + agent contract preserved"
initiative: 6
epic: 11
status: ready-for-dev
created: 2026-05-20
author: Claude (ITCM autonomous mode, parent-context spec authoring per Init 5 effective patterns)
realizes: [FR6-AUTH-1 (partial — gating clauses), FR6-AGENT-1, NFR6-INT-1]
architectural_anchors: [Init 6 Decision M (partial — gating side, not test side), Init 5 Decision C verbatim]
depends_on: [none — E11 entry story]
pre_merge_codex_review: REQUIRED (NFR6-SEC-3)
effort: S (2-3h)
risk: Medium (security boundary; agent regression test mandatory)
---

# Story 11.1 — Backend default-deny gating on SoT + agent contract preserved

## Context

Initiative 5 architecture.md Decision C linia 1489-1490 specified `current_user` for `/api/sot/*` + `/api/catalog/*` GET endpoints — but implementation in `apps/api/app/modules/sot/router.py` shipped without any auth Depends (text: "Public, unauthenticated"). Pre-cutover nginx IP allowlist masked the drift. Story 10.3 cutover removed the allowlist; supplemental finding High-002 surfaced 2026-05-20 ~21:00 UTC.

Hot-fix attempt `64447ff` added `current_member_or_admin` Depends to all 6 SoT GET endpoints. Codex review reverted it at `be43b92` because `current_member_or_admin` rejects the `agent` role → broke NFR5-INT-1 (agent service-account ingestion via `hydrate_local_tree.py`).

This story implements what Decision C ACTUALLY specified: `current_user` (which accepts admin + member + agent — see `apps/api/app/core/auth/dependencies.py:12` `_ALLOWED_ROLES = frozenset({"admin", "agent", "member"})`).

## Acceptance Criteria

**AC-1 — Backend: all 6 SoT GET endpoints gain `current_user` Depends.**
- `apps/api/app/modules/sot/router.py` lines covering 6 endpoints (`/api/categories`, `/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`, `/api/models/{id}/files/{file_id}/content`) gain `_user_id: uuid.UUID = current_user` parameter.
- Import added: `from app.core.auth.dependencies import current_user`.
- Endpoint description text updated from "Public, unauthenticated." to "Requires authenticated user (any role: admin / member / agent). Initiative 6 default-deny posture; see architecture.md § Initiative 6 Decision M for `_PUBLIC_ROUTES` allowlist."

**AC-2 — Agent regression test (the explicit P1-2 fix from 64447ff codex review).**
- New test `test_sot_categories_agent_authenticated_returns_200` (or equivalent) in `apps/api/tests/test_sot_categories.py`: agent-role JWT cookie → `GET /api/categories` returns 200.
- Identical pattern for `test_sot_tags_agent_authenticated_returns_200`, `test_sot_models_list_agent_authenticated_returns_200`, `test_sot_models_detail_agent_authenticated_returns_200`, `test_sot_model_files_agent_authenticated_returns_200`, `test_sot_model_file_content_agent_authenticated_returns_200`.
- These tests close NFR6-INT-1 with mechanical proof that hot-fix 64447ff's P1-2 cannot recur.

**AC-3 — Anonymous-rejection test.**
- For each of the 6 endpoints, a `test_sot_*_anonymous_returns_401` covering: no cookie → 401.

**AC-4 — Member-allowed test.**
- For each of the 6 endpoints, a `test_sot_*_member_authenticated_returns_200` covering: member-role JWT cookie → 200 (assumes pre-seeded test data per existing pattern).

**AC-5 — Admin-allowed test (regression).**
- Existing tests that use admin cookie path continue to PASS. No retroactive failure on existing test suite.

**AC-6 — `test_hydrate_local_tree.py` agent flow continues to work.**
- The hydrate script (`apps/api/scripts/hydrate_local_tree.py`) uses cookie auth (bearer_token path also exists but tests use cookie path). Existing test scaffolding pre-sets `portal_access` cookie on TestClient before invoking `run_hydrate()`. Story 11.1 verifies this STILL works with `current_user` (no scaffolding change needed since `current_user` accepts the agent role that the test cookie has). If test scaffolding was using anonymous calls expecting public read, it must be updated to set agent cookie.

**AC-7 — Full pytest suite PASS.**
- `timeout 600 uv run pytest apps/api/tests/test_sot_*.py apps/api/tests/test_hydrate_local_tree.py` returns 0 (per `feedback_pytest_timeout.md`).
- Full suite `timeout 600 uv run pytest apps/api/tests/` returns 0 (or documented exception per Init 5 retro doc-drift #8 pre-existing fixture-order hang).

**AC-8 — Cutover-smoke Scenario 2 (agent ingestion) PASS post-deploy.**
- Post-deploy `bash infra/scripts/cutover-smoke.sh` Scenario 2 PASS. (Smoke uses agent cookie auth; this validates the production deploy preserves NFR6-INT-1.)

**AC-9 — Pre-merge Codex review (NFR6-SEC-3).**
- `codex review --commit <story-1.1-commit-SHA>` invoked on the dev commit BEFORE ff-merge to main.
- Any P1 finding addressed in follow-up commit(s) before ff-merge.
- Codex review output captured at `_bmad-output/implementation-artifacts/codex-review-11-1-<sha>.md` (mirrors Init 5 NFR5-SEC-2 capture pattern).

## Out of Scope (deferred to other stories)

- **Frontend AuthGate changes** — Story 11.3.
- **Share-scoped asset endpoint** — Story 11.2.
- **Route enforcement pytest test** — Story 11.4 (this story implements the auth posture; Story 11.4 implements the mechanical enforcement test).
- **Audit re-run** — Story 11.5.

## Implementation Notes

- `current_user` is exported from `apps/api/app/core/auth/dependencies.py:77` as `current_user = Depends(_current_user_dep)`. Use as `_user_id: uuid.UUID = current_user` parameter (mirrors `current_admin` usage pattern in existing admin routes).
- The dependency is JWT-only oracle — no DB I/O on the auth boundary. Performance-neutral.
- Agent role JWT issuance follows Init 2 cookie+password flow; tests can mint agent JWT via existing `encode_token` helper (see `test_sot_admin_files.py:31` for admin-pattern reference). Replace `role="admin"` with `role="agent"` for agent-role tests.
- Test fixtures: existing `client` fixture in `apps/api/tests/conftest.py` covers TestClient setup. Agent cookie can be set via `client.cookies.set(ACCESS_COOKIE, agent_jwt)` before each test or via per-file fixture mirroring `test_share_member_permission.py` member-cookie pattern.

## Verification Commands

```bash
# Pre-fix smoke (capture baseline)
curl -fsS -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/categories"   # → 200 (pre-fix; nginx-perimeter-only)

# Apply Story 11.1 patch
# (sot/router.py + tests/test_sot_*.py)

# Run tests
timeout 600 uv run pytest apps/api/tests/test_sot_*.py apps/api/tests/test_hydrate_local_tree.py -v

# Post-fix smoke (anonymous now 401)
curl -fsS -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/categories"   # → 401 (post-fix; portal-auth)

# Post-fix authenticated smoke (member cookie)
curl -fsS -o /dev/null -w "%{http_code}\n" -b "portal_access=<member-jwt>" "http://localhost:8000/api/categories"   # → 200

# Codex review (pre-merge)
git add -A
git commit -m "fix(api): Story 11.1 default-deny on SoT GET endpoints (Initiative 6)"
codex review --commit HEAD --output-last-message /tmp/codex-review-11-1.json
# Address any P1 findings before ff-merge

# Deploy verification
bash infra/scripts/cutover-smoke.sh   # 4/4 PASS, especially Scenario 2 (agent)
```

## Risk Mitigation

- **Risk: agent regression (P1-2 recurrence).** Mitigation: AC-2 explicit agent-200 tests at every endpoint; pre-merge codex review verifies the diff.
- **Risk: existing test breakage from anonymous → 401 flip.** Mitigation: AC-4/AC-5 cover all auth paths; AC-7 full-suite assertion.
- **Risk: share-asset URLs (P1-1 recurrence).** Mitigation: STORY 11.2 (NOT this story) introduces the share-scoped asset endpoint; this story's deploy keeps `/api/models/{m}/files/{f}/content` gated on `current_user` which means share recipients lose access externally until Story 11.2 ships. EXPECTED REGRESSION acknowledged in deploy plan: sibling configs allowlist `70cb5ba` keeps external anonymous → 403 during the Initiative 6 build window; share recipients on LAN still work; share recipients external broken until Story 11.7 sibling rollback. This is the operator-accepted trade-off per SCP §1.4 production state table.

## Definition of Done

- [ ] AC-1 through AC-9 all PASS
- [ ] Pre-merge codex review captured at `_bmad-output/implementation-artifacts/codex-review-11-1-<sha>.md`
- [ ] Commit ff-merged to main
- [ ] Deploy fired (`infra/scripts/deploy.sh`) per `feedback_auto_deploy_dev.md`
- [ ] Post-deploy smoke `bash infra/scripts/cutover-smoke.sh` 4/4 PASS
- [ ] Sprint-status flipped: `11-1-backend-default-deny-sot-agent-contract: backlog → done` with closing-commit SHA
