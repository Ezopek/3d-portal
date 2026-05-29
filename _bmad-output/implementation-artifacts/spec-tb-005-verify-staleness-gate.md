---
title: 'TB-005 verify-symbolication.sh false-negative on partial-image deploys'
type: 'bugfix'
created: '2026-05-11'
status: 'done'
route: 'one-shot'
---

# TB-005 verify-symbolication.sh false-negative on partial-image deploys

## Intent

**Problem:** When `deploy.sh` rebuilds the API image but the web image is fully layer-cached (no `apps/web/` source changes — API-only fix, doc-only commit that triggers API rebuild, infra-only change), the running web SDK still reports the OLD release identity. The new verify run injects a smoke event whose release tag is derived from the running SDK (= OLD release), polls for a matching event with the smoke.run_id UUID, and... actually matches it just fine, because smoke poll filters on `smoke.run_id`, not on release tag. The real symptom: under SOME cache-hit scenarios (specifically when no fresh web build means the SDK's release tag doesn't match the just-built release identity expected by GlitchTip release tracking), verify times out. Each false-negative pollutes the verify-history that NFR-R3 treats as a real signal; operator habituated to FAILED markers being normal → real symbolication regression mixed into noise + missed.

**Approach:** Add a staleness gate in `verify-symbolication.sh` that, when invoked from `deploy.sh` (via exported `DEPLOY_START_TS` + `PORTAL_VERSION`), inspects `portal-web:$PORTAL_VERSION` via `docker inspect --format '{{.Created}}'`. If the image was created BEFORE this deploy started → exit 5 (SKIPPED), write `SKIPPED\tweb-image-cached` to `.last-verify`. Standalone CLI invocations (no DEPLOY_START_TS in env) always run the full verify. Failure-preserving guard: never overwrite a prior `FAILED` marker with `SKIPPED` — cache-hit deploys following a broken-symbolication deploy fall through to the full verify path so the failure signal is not erased.

## Suggested Review Order

1. [Diff — `infra/scripts/verify-symbolication.sh`](../../infra/scripts/verify-symbolication.sh) — staleness gate at lines ~165–198. Read the comment block first; it explains: (a) opt-in via DEPLOY_START_TS, (b) graceful fall-through on docker inspect failures, (c) the P1-A FAILED-preservation guard.
2. [Diff — `infra/scripts/deploy.sh`](../../infra/scripts/deploy.sh) — `DEPLOY_START_TS` + `PORTAL_VERSION` export at lines 13–22; new `case 5)` arm at line 102; defensive `unset` at script end.
3. [Diff — `docs/operations.md`](../../docs/operations.md) — three-signal failure model updated to include SKIPPED state and FAILED-preservation contract.
4. [Triage backlog entry → Declined/done](../triage-backlog.md) — TB-005 row closed with commit reference.
5. [Sprint status `last_updated`](./sprint-status.yaml).

## Adversarial review summary

`feature-dev:code-reviewer` (no conversation context) returned 0×P0 + 3×P1 + 2×P2 + 3×OK. All P1/P2 applied:

- **P1-A** (92) — SKIPPED would overwrite a prior FAILED marker, erasing the stale-verify signal on follow-up cache-hit deploys. Fix: read `.last-verify` content; if FAILED, emit warning + fall through to full verify.
- **P1-B** (85) — `PORTAL_VERSION` cmdline override clobbered by `set -a; source infra/.env; set +a` BEFORE the gate constructs the image tag. Fix: snapshot inbound env into `_inbound_*` locals before sourcing .env; gate uses the locals.
- **P1-C** (88) — `docs/operations.md` three-signal failure model documented only OK/FAILED. Fix: extend to OK/FAILED/SKIPPED + document the FAILED-preservation guard.
- **P2-A** (82) — Lingering `DEPLOY_START_TS` in operator's shell could silently skip manual `bash verify`. Fix: `unset DEPLOY_START_TS PORTAL_VERSION` at end of `deploy.sh`.
- **P2-B** (80) — `docker inspect <image> --format` non-standard arg order. Fix: `docker inspect --format <tmpl> <image>`.

## Live e2e (pre-commit)

| Scenario | Result |
|---|---|
| Standalone (no DEPLOY_START_TS) | Full verify path, exit 0, smoke 77 cleaned |
| Gate ON, future DEPLOY_START_TS, .last-verify=OK | SKIPPED, exit 5, `.last-verify` rewritten as `SKIPPED web-image-cached` |
| Gate ON, future DEPLOY_START_TS, .last-verify=FAILED (P1-A guard) | Warning printed, falls through to full verify, `.last-verify` content preserved as FAILED |

**Empirical finding during integration test (commit 305512d):** under the current `deploy.sh` + `apps/web/Dockerfile` chain, the web image NEVER cache-hits because `deploy.sh` exports a fresh `VITE_BUILD_TIME` on every invocation → the Dockerfile's `RUN npm run build` step has a different `ENV` snapshot each time → BuildKit cache misses → web image always rebuilds. Two consecutive deploys of commit `305512d` both produced fresh images with `.Created` newer than `DEPLOY_START_TS` → gate did not fire → normal verify ran and succeeded. TB-005 is therefore defense-in-depth for the current setup: the gate is correct, opt-in, and graceful — but the cache-hit scenario it protects against requires either (a) a future deploy.sh change to enable reproducible / time-stable builds, (b) operator manually rebuilding parts of the stack outside of `deploy.sh`, or (c) Docker layer caching changes that ignore `VITE_BUILD_TIME` drift. The gate is harmless when it doesn't fire; activates correctly when those conditions emerge.

## Known limitation (documented)

`infra/.env` exports `PORTAL_VERSION=0.1.0` and the script sources it. The P1-B cmdline-override capture (`_inbound_portal_version`) preserves an operator's `PORTAL_VERSION=X bash deploy.sh` override at the gate level, but `docker compose build` in deploy.sh and image-tagging downstream depend on the same value resolving consistently — these are out of TB-005's scope.
