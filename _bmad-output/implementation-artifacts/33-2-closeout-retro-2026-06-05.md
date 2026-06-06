---
title: Story 33.2 — validated Orca profile import/publish — closeout learnings
date: 2026-06-05
initiative_scope: [21]
epic: E33
story: 33.2 (PROFILE-ADMIN-2) — validated profile import/publish
artifact_class: story-level closeout learnings (NOT the epic retrospective)
facilitator: Claude (Opus 4.8 1M, repo-local BMAD author of record); Laura = operator-side controller / ITCM liaison; Michał = operator/project lead
mode: reflective post-merge / post-deploy story close-out. ARTIFACT-ONLY — no app code touched, no dev-story run, no commit / ff-merge / deploy performed by this artifact.
story_spec: _bmad-output/implementation-artifacts/33-2-validated-profile-import-publish.md
scp: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-04-profile-admin.md (approved 2026-06-04)
feature_commits_on_main:
  - 6a242e0  # feat(slicer): import validated profiles
  - 31bcf0c  # fix(slicer): preserve vendored profile file metadata
  - 3c2b8b7  # docs(bmad): close E33.2 profile import
deployed_release: 0.1.0+31bcf0c (live on .190)
reviews:
  - Hermes fallback subagent (Gemini/Codex CLIs unavailable at the time) → REQUEST_CHANGES (path traversal + non-atomic publish) → fixed
  - Codex contracted review (focused diff) → REQUEST_CHANGES (audit-rollback-after-publish + unsafe file.filename) → fixed → re-review APPROVE
  - Gemini contracted review → UNAVAILABLE (429 MODEL_CAPACITY_EXHAUSTED / hanging direct review); parked as Laura ops Kanban t_504aaff7
gates: full check-all.sh 16/16 all green TWICE (post-Codex-fix + post-permission-fix)
predecessor_retro: epic-32-retro-2026-06-02.md
---

# Story 33.2 — validated Orca profile import/publish — closeout learnings

> **Scope of this artifact.** This is a **story-level closeout learnings** note for Story 33.2, NOT the Epic 33 retrospective. Epic 33 is still `in-progress` in `sprint-status.yaml` (33.1 `done`, 33.2 `done`, 33.3 `backlog`), and `epic-33-retrospective` stays `backlog` — reserved for the operator-driven epic-close ceremony per the `epic-X-retrospective` convention (Init 19 G4). This artifact does **not** flip that row, does not run the vanilla `bmad-retrospective` epic ceremony, and changes no application code. It exists to capture the cross-cutting code / runtime / toolchain / controller lessons from 33.2 while context is fresh, so the epic retro and the next slice start from a truthful baseline. The full implementation record (ACs, tasks, file list, gate logs) already lives in the story spec — this note deliberately does not duplicate it.

## §1 What shipped

Story 33.2 (PROFILE-ADMIN-2, Decision AL) added the first in-product **write** to the operator-managed vendored Orca profile tree: `POST /api/admin/profiles/import` (admin-gated, out of `_PUBLIC_ROUTES`, CSRF-automatic) that validates an uploaded profile partial against the live system tree by **reusing `resolve()` verbatim** (`StagedProfileSource` + `_NoPersistBundleStore` — validation neither reads nor writes the append-only bundle store), enforces compatibility **before** any write, then atomically publishes the validated intent plus a v1 sidecar `.manifest.json` and writes a leak-fenced `slicer_profile.import` audit event. The 33.1 inventory read was extended (additive, read-only) to surface the manifest `portal_label`; the frontend's previously-inert `ImportPlaceholder` became a live, fail-closed import affordance (`useImportProfile`, multipart via `api()`, no optimistic flip, localized rejection reasons, zero inline hex).

Final state: three curated commits on `main` (`6a242e0` feature, `31bcf0c` runtime-metadata fix, `3c2b8b7` docs close-out); deployed release **0.1.0+31bcf0c** live on `.190`; Codex re-review **APPROVE**; full `check-all.sh` **16/16 green twice**; live runtime import smoke on `.190` confirmed an offerable TPU/standard slot with a sanitized filename, v1 manifest, stable intent hash across a second smoke, and preserved `ezop:ezop 664` file metadata.

## §2 What went well

- **W1 — `resolve()` reused verbatim, no second SoT.** Validation rode the real resolver against the real system tree (uploaded partials fed from memory), and the sidecar manifest was kept as a point-in-time record only — `compatibility.py` stayed the single live compat gate (AC-10). No dual-SoT drift was introduced on a write-path story, which is exactly where drift usually creeps in.
- **W2 — write-before-write safety was honored at spec time and held.** Gate order (size → shape → compatibility → structural resolve → atomic publish → manifest → audit) ensured an incompatible or malformed upload is rejected **before** the tree is touched; tests prove byte-identical tree + no escape-marker file + no temp leftover on every rejection path.
- **W3 — review caught real, runtime-invariant defects, and every fix landed under TDD** with a regression test proven red-pre-fix / green-post-fix, followed by re-review. The data-integrity-heavy surface got the scrutiny it warranted (details in §3).
- **W4 — the live GO gate worked as designed.** Deploy was correctly **paused** after Codex returned REQUEST_CHANGES; live runtime smoke only ran after the contracted reviewer re-reviewed APPROVE and the full gate was green. The earliest-honest baseline (a real runtime bug, §3.2) was caught by that very live smoke, not asserted away.

## §3 Findings by class

The point of separating these classes is that they have different prevention strategies — a green dev gate addresses §3.1 but is structurally blind to §3.2, and neither touches §3.3/§3.4.

### §3.1 Code defects (caught by review, fixed under TDD)

| # | Defect | Reviewer | Fix |
|---|---|---|---|
| C1 | `printer_ref` path traversal on the write path (`../`, separators, absolute) could escape the intents root. | Hermes fallback (Critical) | `is_safe_printer_ref` charset/segment gate (2b) → `422 invalid_printer_ref` + `is_within_intents_root` containment assert (4b); no write on traversal. Accept/reject table + endpoint traversal tests. |
| C2 | intent + manifest published as two independent atomic writes — a manifest-write failure left a live intent paired with a stale/missing manifest. | Hermes fallback (High) | Two-phase publish: stage both temps → commit intent → commit manifest; on manifest failure roll the intent back to prior state (fresh import leaves nothing; re-import restores the prior pair); no temp leftovers. Injected-failure tests for both fresh and re-import. |
| C3 | audit `record_event` failure **after** publish could leave a live, unaudited intent+manifest pair. | Codex contracted (Important, REQUEST_CHANGES) | Endpoint snapshots the prior intent+manifest before publish and restores the pair if the required audit write fails after publish. |
| C4 | raw user-controlled multipart `file.filename` stored verbatim into manifest + audit payload. | Codex contracted (Important, REQUEST_CHANGES) | `sanitize_original_filename(...)` — basename-only, control/percent-escape replacement, trim + truncate — applied before both sidecar manifest and audit payload. |

C3/C4 fixed → Codex re-review **APPROVE** (Critical=None, Important=None, Minor=None). C1/C2 were closed before the Codex round.

### §3.2 Runtime / config defect (only a real RW smoke could find it)

- **R1 — publish wrote bind-mounted files as `root:root 600`.** The atomic `mkstemp → fsync → os.rename` publish created the new vendored files owned by the container UID with restrictive perms, instead of preserving the operator-managed tree's `ezop:ezop 664`. The full dev gate was **green** when this shipped — the defect lives entirely in the runtime RW-mount + ownership interaction, which the in-repo suite (real-tmp-tree, but same-UID, no bind-mount) structurally cannot exercise. Caught by the post-deploy live smoke on `.190`; fixed in `31bcf0c` to preserve the existing vendored file's owner/group/mode; second live smoke confirmed `ezop:ezop 664` preserved for both intent and manifest. **File metadata/permissions are part of write-path correctness for an operator-managed shared tree, not an ops afterthought.**

### §3.3 Toolchain / process defects (infra debt — track, don't waive)

- **T1 — Gemini contracted-review lane was unavailable/unstable.** The default wrapper returned `429 RESOURCE_EXHAUSTED / MODEL_CAPACITY_EXHAUSTED` (gemini-3-flash-preview) and a direct `gemini-2.5-pro` focused-diff attempt did not produce a verdict in bounded wait. This is a **tool/provider availability** problem, not a code finding, and was correctly parked as Laura ops Kanban `t_504aaff7` ("stabilize Gemini contracted review wrapper") rather than silently waived. Recurs with Init 19/20's host-side Gemini-CLI unavailability — treat as standing infra debt, not a per-story surprise.
- **T2 — rich shell prompts / one-line SSH quoting caused repeated friction** during the gate / review / deploy commands (the failure mode AGENTS.md § "Remote agent prompting over SSH" and the global SSH rules already warn about). Complex agent/gate/deploy invocations should default to **prompt files + remote scripts on stdin**, not multiplexed one-line quoted commands — this story is another data point that the file/stdin path is the default, not the fallback.

### §3.4 Controller / operator lessons (with critique where warranted)

1. **Default to prompt files / remote scripts for complex agent, gate, and deploy commands.** The friction in §3.3-T2 was self-inflicted by reaching for one-line quoted SSH first; the operator/controller path should make file-or-stdin prompting the reflex. *(Critique of the controller lane: the policy already exists in AGENTS.md — the gap was application discipline, not missing rule.)*
2. **A green dev gate before live smoke is necessary but not sufficient.** §3.2-R1 only surfaced in the runtime RW smoke. For any story that writes to a bind-mounted / operator-managed tree, the closeout checklist must include a **live RW smoke that asserts file owner/group/mode**, not just HTTP status + content. Dev-gate-green is not a deploy GO on write-path stories.
3. **Reviewer-lane honesty: a fallback verdict does not supersede the contracted reviewer's later verdict.** Whatever a fallback/availability-substitute reviewer returns, once the contracted reviewer (here Codex) is reachable and returns REQUEST_CHANGES, that is the gate — and deploy stayed paused until its re-review APPROVE. The lane discipline held; the lesson is to keep it explicit so an "earlier approved" reading can never be used to skip the real verdict.
4. **Tool/provider instability is infra debt, tracked — not a silent waiver.** Gemini's unavailability (§3.3-T1) was logged to a Kanban card with an honest "not a code approval" framing rather than recorded as a passed review. Keep that framing: an unavailable reviewer is a *gap to track*, never a *green check*.
5. **File metadata/permissions are write-path correctness** for operator-managed vendored trees (the §3.2-R1 generalization). Bake an ownership/permission assertion into the test or smoke contract for any future write to a shared, externally-owned tree (relevant immediately to Story 33.3 lifecycle edit/disable/delete, which mutates the same tree + sidecar manifests).
6. **Live GO was correctly gated on fresh review + fresh gates.** Deploy was paused after Codex RC and only resumed after re-review APPROVE + 16/16 green — the right sequencing, recorded here as a confirmation of the gate, not a change to it.

## §4 Action items (evidence-derived only)

These are derived strictly from the findings above — no speculative roadmap. None are silently written elsewhere; the epic-close retro / operator decides whether any become tracked `triage-backlog.md` items.

- **AI-1 (process, immediate carry to 33.3):** add an explicit **owner/group/mode assertion** to the write-path test or live-smoke contract for any story that writes the operator-managed vendored tree. Source: §3.2-R1 + §3.4-5. Directly relevant to Story 33.3 (lifecycle mutate/delete on the same tree).
- **AI-2 (infra debt, already filed):** drive Laura ops Kanban `t_504aaff7` (stabilize the Gemini contracted-review wrapper) to closure, or formally adopt a contracted fallback reviewer so a story is never blocked on a single flaky review lane. Source: §3.3-T1.
- **AI-3 (process discipline):** make **prompt-file / stdin** the default transport for complex agent/gate/deploy commands; stop reaching for one-line quoted SSH first. Source: §3.3-T2 + §3.4-1. (No new rule — AGENTS.md already mandates it; this is an adherence reminder.)
- **AI-4 (closeout-checklist candidate):** for write-path stories, add "live RW smoke asserting file metadata + atomicity, run only after contracted-review APPROVE" as a named deploy-GO precondition. Source: §3.2 + §3.4-2/6. Candidate for the epic-33 retro to codify or send to triage.

## §5 Verification performed by this artifact

- `git log -1` on each of `6a242e0`, `31bcf0c`, `3c2b8b7` confirmed subjects match the closeout record; `git log --oneline` confirmed all three are on `main` with `3c2b8b7` as the docs close-out.
- Story spec `33-2-validated-profile-import-publish.md` Final-closeout + Dev Agent Record re-read; all findings/fixes/gate logs cited above are transcribed from it (Codex RC→APPROVE, two 16/16 `check-all.sh` logs, both deploy logs, live smoke result, Gemini-unavailable + Kanban `t_504aaff7`).
- `sprint-status.yaml` re-read: confirmed `33-2 ... : done`, `epic-33: in-progress`, `epic-33-retrospective: backlog` — this artifact intentionally leaves all three untouched (it is not the epic ceremony).
- No application code, no `sprint-status.yaml`, no deploy touched by this artifact. No secrets/tokens/passwords recorded.
