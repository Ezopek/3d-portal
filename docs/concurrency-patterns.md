# Concurrency patterns

> **Status:** Living catalog. Curated from Epic 6 (invites + ratelimit), Epic 7 (TOTP/2FA), and Epic 8 (admin panel) dev work. Each pattern captures a recurring problem + the in-repo solution shape + the citation back to the code so a new contributor can read the working example before reaching for it.
>
> **Why this exists.** Epic 8 retrospective §A12 flagged that the same primitives (`asyncio.to_thread`, atomic `GETDEL`, race-safe `UPDATE ... WHERE`, restore-on-fail wrap, monotonic CAS predicate, commit-guard flag) were re-derived from first principles in three to four separate stories. A short reference index amortises that learning so subsequent stories (Epic 9 audit, Initiative 6 onwards) reach for the documented shape directly.
>
> **Scope.** This file is a pattern index, not a tutorial. Each entry is ≤25 lines: one-line summary, why-it-matters, minimal example (5-10 lines), and a `see:` line pointing at the in-repo precedent. Read the cited code for full context.

---

## CC1 — `asyncio.to_thread` for blocking work in async handlers

**Summary.** Wrap CPU-bound or synchronous-IO work in `asyncio.to_thread(...)` so the ASGI event loop is not blocked.

**Why it matters.** FastAPI handlers run on the event loop; a synchronous `bcrypt.checkpw` or a sync SQLAlchemy `engine.begin()` block freezes the loop and serialises every concurrent request behind it. The fix is to push the blocking call into the default executor.

```python
# apps/api/app/modules/auth/router.py:83
user = await asyncio.to_thread(_lookup_user)
# apps/api/app/modules/auth/router.py:154
secret = await asyncio.to_thread(_mint_refresh_row)
# apps/api/app/core/auth/middleware.py:175
await asyncio.to_thread(_commit_last_active)
```

**See:** `apps/api/app/modules/auth/router.py:83,154` (bcrypt verify + refresh-row mint) · `apps/api/app/core/auth/middleware.py:175` (last-active monotonic write) · introduced in commit `80eebc9` (Story 8.1 LastActiveMiddleware) and Codex P2 fix-up `ddb9f14` (Story 8.3).

---

## CC2 — Atomic `GETDEL` for single-use Redis tokens

**Summary.** Replace the two-step `GET + DEL` token-claim with a single `GETDEL` Redis command so the read-then-delete is atomic across uvicorn workers.

**Why it matters.** `GET` followed by `DEL` is two round-trips with an interleaving window. Under concurrent traffic two workers can both `GET` the same token before either `DEL`s, and both mint a session — the canonical single-use-token-burned-twice bug. `GETDEL` (Redis 6.2+) is one indivisible op: at most one caller sees the value, the rest see `None`.

```python
# apps/api/app/modules/auth/totp/service.py:229
claimed = await self._redis.execute_command("GETDEL", key)
if claimed is None:
    raise EnrollmentTokenInvalid
```

**See:** `apps/api/app/modules/auth/totp/service.py:229` (TOTP enrollment claim) · `apps/api/app/modules/auth/totp/router.py:369` (partial-token claim during /verify) · `apps/api/app/modules/auth/password_reset/service.py:89` (password-reset claim) · introduced across commits `9e6c0e4` (Story 7.2 enrollment), `a9bea16` (Story 7.3 partial-token verify), `aaac593` (Story 8.5 password-reset).

---

## CC3 — Conditional `UPDATE` for race-safe state transition

**Summary.** Push the read-modify-write check into a single `UPDATE ... WHERE <invariant>` so the database — not the application — picks the winner of a state transition race.

**Why it matters.** Two async handlers reading the same row, computing "is this still claimable?", and writing back can interleave between the read and the write. Encoding the invariant in the `WHERE` clause guarantees only one row update succeeds; `rowcount == 0` is the unambiguous "another concurrent caller won" signal.

```python
# apps/api/app/modules/auth/totp/router.py:389
result = session.execute(
    update(RecoveryCode)
    .where(RecoveryCode.id == matched_row.id)
    .where(RecoveryCode.used_at.is_(None))
    .values(used_at=used_at_value)
)
if result.rowcount == 0:
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_code")
```

**See:** `apps/api/app/modules/auth/totp/router.py:389-402` (recovery-code consumption) · introduced in commit `a9bea16` (Story 7.3 Codex P2-4).

---

## CC4 — Restore-on-fail for destructive claim → action sequences

**Summary.** When a single-use claim (`GETDEL`) precedes a downstream action that can fail (DB commit, encryption, mint), best-effort restore the claim on failure so the operator can retry without re-issuing the token.

**Why it matters.** Once `GETDEL` consumes a token, a subsequent failure leaves the user stuck — the token is gone and the action did not complete. Re-`SET`-ing the token in a `try/except` lets the user retry the same flow; wrapping the restore in `contextlib.suppress(Exception)` ensures a flaky Redis on the restore path does not mask the original error.

```python
# apps/api/app/modules/auth/totp/service.py:215-258 (shape)
claimed = await self._redis.execute_command("GETDEL", key)
if claimed is None:
    raise EnrollmentTokenInvalid
try:
    # ... DB writes, encryption, etc.
    session.commit()
except Exception:
    with contextlib.suppress(Exception):
        await self._redis.set(key, claimed, ex=ttl_seconds)
    raise
```

**See:** `apps/api/app/modules/auth/totp/service.py:215-258` (enrollment restore) · mirrored in partial-token verify and password-reset claim · introduced in commit `9e6c0e4` (Story 7.2).

---

## CC5 — Monotonic CAS predicate for timestamp columns

**Summary.** When two writes can race on the same `now`-like column, encode forward-monotonicity in the `WHERE` clause (`col IS NULL OR col < :now`) so the column never moves backwards.

**Why it matters.** `LastActiveMiddleware` writes `user.last_active_at` from every authenticated request. Under bursty load two concurrent middlewares capture timestamps `t1 < t2` but execute their `UPDATE`s in reverse order — `last_active_at` ends up at `t1`, off by the burst window. The predicate `last_active_at IS NULL OR last_active_at < :now` lets the database drop the stale write, no application-level locking required.

```python
# apps/api/app/core/auth/middleware.py:168-175
stmt = sa.text(
    "UPDATE user SET last_active_at = :now WHERE id = :user_id "
    "AND (last_active_at IS NULL OR last_active_at < :now)"
).bindparams(sa.bindparam("user_id", type_=sa_uuid_type()))
with engine.begin() as conn:
    conn.execute(stmt, {"now": write_now, "user_id": user_id})
```

**See:** `apps/api/app/core/auth/middleware.py:155-175` · introduced in commit `80eebc9` (Story 8.1) and tightened by Codex P2 fix-up `ddb9f14` (Story 8.3).

---

## CC6 — Commit-guard flag preventing post-commit restore from minting duplicate state

**Summary.** A boolean `_commit_done = False` flag flipped to `True` immediately after `session.commit()` gates the restore-on-fail (CC4) branch so a post-commit downstream failure does not re-mint a token whose work already produced durable state.

**Why it matters.** Step 1 `GETDEL` consumes the token. Step 2 `session.commit()` durably persists the new session/refresh-row. Step 3 (e.g. response serialization, log emission) raises. Without a guard, the generic `except: restore(token)` branch re-`SET`s the consumed token to Redis — and now the same token can be replayed to mint a *second* session, even though the first commit already succeeded. The flag closes the window: restore is only attempted while `_commit_done is False`.

```python
# apps/api/app/modules/auth/totp/router.py:380-490 (shape)
_commit_done = False
try:
    # ... GETDEL claim, recovery-code UPDATE, refresh-row mint
    session.commit()
    _commit_done = True
    # ... post-commit work that may still raise
except Exception:
    if not _commit_done:
        with contextlib.suppress(Exception):
            await redis.set(partial_key, claimed, ex=ttl)
    raise
```

**See:** `apps/api/app/modules/auth/totp/router.py:385-490` · introduced in commit `a9bea16` (Story 7.3) — gap was caught in Codex review of the initial restore-on-fail draft (the initial draft restored unconditionally and was flagged as a duplicate-session-mint risk).

---

## Reading order

A new contributor encountering these patterns should read in the order: **CC1 (async-safety)** → **CC2 (atomic claim)** → **CC4 (restore-on-fail wrap)** → **CC6 (commit-guard for CC4)** → **CC3 (race-safe UPDATE)** → **CC5 (monotonic CAS)**. The first four form the auth/2FA token-claim machinery; CC3 and CC5 are independent primitives that apply wherever a row-level race exists.
