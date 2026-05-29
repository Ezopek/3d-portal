# Story 6.1: Alembic migration `0012_invite_tokens` + invite-token primitives

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want the Alembic `0012_invite_tokens` migration + the `apps/api/app/modules/invite/` package skeleton (TTL preset enum, `InviteToken` SQLModel, `hash_token()` helper) + the `KNOWN_ENTITY_TYPES` audit-registry expansion + the structured-log token-redaction filter,
so that the downstream E6 stories (6.2 service, 6.3 admin endpoints, 6.4 public `/register`) can build on a schema that survives Alembic round-trip, primitives that satisfy `record_event()` without `ValueError`, and a logging pipeline that never leaks cleartext invite-token strings through GlitchTip-visible structured records.

## Acceptance Criteria

**AC-1 — Alembic migration `0012_invite_tokens` round-trip.**

- Given the head Alembic revision in `apps/api/migrations/versions/` is `0011_index_ext_link_url`,
- When `apps/api/migrations/versions/0012_invite_tokens.py` is created with `down_revision = "0011_index_ext_link_url"`, `revision = "0012_invite_tokens"`, an `upgrade()` that creates the `invite_tokens` table per Decision B's column list (with the Init-0-grounded type corrections in Drift 3 below) plus the three indexes (`ux_invite_tokens_token_hash` UNIQUE on `token_hash`, `ix_invite_tokens_generated_at` on `generated_at` DESC, `ix_invite_tokens_used_by_user_id` on `used_by_user_id`), and a `downgrade()` that drops the indexes then the table,
- Then `alembic upgrade head` against a fresh tmpdir SQLite database completes with exit code 0 and the resulting `invite_tokens` table exposes all 10 columns + 3 indexes via `sqlite_master`,
- And `alembic downgrade -1` cleanly drops the table + indexes (zero residual artifacts in `sqlite_master`),
- And `alembic upgrade head` re-runs cleanly after the downgrade (idempotency check — round-trip is fully reversible),
- And `alembic upgrade head` against the production `.190` SQLite (executed by `infra/scripts/deploy.sh` after merge) advances `alembic_version.version_num` from `0011_index_ext_link_url` to `0012_invite_tokens` without manual intervention.

**AC-2 — Invite-token primitives module exports.**

- Given the path `apps/api/app/modules/invite/` does not yet exist in the repo,
- When `apps/api/app/modules/invite/__init__.py` is created (empty package stub; `router.py` + `service.py` + `admin_router.py` ship in Stories 6.2 / 6.3) and `apps/api/app/modules/invite/models.py` is created,
- Then `models.py` exports `class InviteTTLPreset(IntEnum)` with exactly four members: `ONE_DAY = 86400`, `THREE_DAYS = 259200`, `SEVEN_DAYS = 604800`, `THIRTY_DAYS = 2592000` (values match Decision B verbatim),
- And `models.py` exports `class InviteToken(SQLModel, table=True)` with `__tablename__ = "invite_tokens"` and columns matching Decision B's table 1:1 (with Drift 3 type corrections applied — UUID PK + `uuid_fk` for FKs to `user.id`, `UTCDateTime` for timestamp columns, `_now_utc` default for `generated_at`, all per the Init 0 `_audit.py` / `_helpers.py` conventions),
- And `models.py` exports `def hash_token(token: str) -> str` returning `hashlib.sha256(token.encode("utf-8")).hexdigest()` (64-character lowercase hex string),
- And `from app.modules.invite.models import InviteTTLPreset, InviteToken, hash_token` succeeds with no `ImportError` from a Python REPL with the `apps/api` package on `PYTHONPATH`,
- And `hash_token("test")` returns the deterministic SHA-256 digest `9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08` (regression-tested as the SHA-256 of the byte string `b"test"`).

**AC-3 — `KNOWN_ENTITY_TYPES` audit-registry expansion.**

- Given `KNOWN_ENTITY_TYPES` in `apps/api/app/core/audit.py` currently holds the 12-entry closed `frozenset[str]` (`catalog`, `category`, `model`, `model_external_link`, `model_file`, `model_note`, `model_print`, `render_selection`, `share_token`, `tag`, `thumbnail_override`, `user`),
- When `KNOWN_ENTITY_TYPES` is extended by adding the single entity-type `"invite_token"` (per Drift 2 below — the actions `auth.invite.generated` / `auth.invite.used` / `auth.invite.revoked` are free-text values for the `action` column, NOT registered in `KNOWN_ENTITY_TYPES`, which is the closed set of entity-type values),
- Then `record_event(engine, action="auth.invite.generated", entity_type="invite_token", entity_id=<some_uuid>, actor_user_id=<admin_uuid>)` succeeds with no `ValueError` and persists a row to `audit_log` with the matching action+entity_type pair,
- And `record_event(engine, action="auth.register.success", entity_type="user", entity_id=<new_user_uuid>, actor_user_id=<new_user_uuid>)` succeeds — register-success reuses the existing `"user"` entity_type per the precedent in `apps/api/app/modules/auth/router.py` for `auth.login.fail`,
- And `record_event(engine, action="anything", entity_type="invite_token_typo", entity_id=None, actor_user_id=None)` still raises `ValueError("unknown entity_type ...")` — the closed-set forward guard is preserved,
- And `apps/api/tests/test_audit.py::test_known_entity_types_covers_all_call_site_resources` is updated in the SAME commit to include `"invite_token"` in its `expected` set (this test asserts EXACT EQUALITY against `KNOWN_ENTITY_TYPES` and would otherwise fail immediately).

**AC-4 — Logger token-redaction filter.**

- Given `apps/api/app/core/logging.py` currently exposes `JsonFormatter` and `configure_logging()` with no field-redaction filter attached,
- When `apps/api/app/core/logging.py` is updated to add `class TokenRedactionFilter(logging.Filter)` whose `filter(record)` method (a) regex-substitutes `\btoken=[^&\s"']+` with the literal `token=<redacted>` in `record.msg` and across every element of `record.args`, AND (b) for any pass-through `extra=` dict that surfaced as an attribute named `"token"` on the `LogRecord`, replaces that attribute's value with the literal string `<redacted>`,
- And `configure_logging()` is updated to attach a `TokenRedactionFilter` instance to the `StreamHandler` (via `handler.addFilter(...)`) BEFORE the formatter is set, so the filter mutates the record before `JsonFormatter.format()` reads it,
- Then a `LogRecord` constructed via `logger.info("GET /register?token=abc&foo=bar")` produces a `JsonFormatter`-rendered JSON line whose `message` field is `"GET /register?token=<redacted>&foo=bar"` (`foo=bar` and the rest of the URL untouched),
- And a record constructed via `logger.info("registered", extra={"token": "abc", "user_id": "x"})` produces a JSON line where the pass-through `token` key (if surfaced via the existing `passthrough_keys` extension in `JsonFormatter`) renders as `<redacted>` and `user_id` renders untouched,
- And a record without any `token` substring or `token` key (the negative path) renders byte-identical to the pre-filter output (regression-asserted),
- And a regex scan across the rendered JSON for any of the three above cases finds zero occurrences of the cleartext `"abc"` test-value substring (final defense-in-depth assertion).

## Tasks / Subtasks

- [x] **T1 — Author Alembic migration `0012_invite_tokens.py` (AC-1)**
  - [x] T1.1 Create `apps/api/migrations/versions/0012_invite_tokens.py` with module-docstring + `revision = "0012_invite_tokens"` + `down_revision = "0011_index_ext_link_url"` + `branch_labels = None` + `depends_on = None`, following the `0009_refresh_tokens.py` shape (not the `0011_index_ext_link_url.py` shape, which is a single-statement index addition).
  - [x] T1.2 In `upgrade()`, `op.create_table("invite_tokens", ...)` with the 10 columns per Decision B (Drift 3 corrections applied — UUID PK, UUID FKs to `"user.id"` with `ondelete="SET NULL"` matching `_audit.AuditLog.actor_user_id` precedent, `nullable=True` on `generated_by_user_id` to honour the Decision A "DB row outlives Redis TTL" semantics): `id` UUID PK, `token_hash` VARCHAR(64) NOT NULL UNIQUE, `role` VARCHAR(16) NOT NULL, `generated_by_user_id` UUID NULL FK `user.id` ondelete=SET NULL, `generated_at` DateTime NOT NULL, `ttl_seconds` INTEGER NOT NULL, `used_by_user_id` UUID NULL FK `user.id` ondelete=SET NULL, `used_at` DateTime NULL, `used_from_ip` VARCHAR(45) NULL, `revoked_at` DateTime NULL.
  - [x] T1.3 In `upgrade()`, `op.create_index(...)` three indexes: `ux_invite_tokens_token_hash` UNIQUE on `["token_hash"]`, `ix_invite_tokens_generated_at` on `["generated_at"]` (DESC ordering enforced at query time in 6.3 — SQLite ignores per-column ordering hints), `ix_invite_tokens_used_by_user_id` on `["used_by_user_id"]`.
  - [x] T1.4 In `downgrade()`, drop the three indexes first (`op.drop_index(...)`) then `op.drop_table("invite_tokens")`. Matches the `0009_refresh_tokens.py` downgrade ordering.
  - [x] T1.5 Add a one-shot pytest at `apps/api/tests/test_migration_0012.py` that creates a temp SQLite DATABASE_URL, drives `alembic.command.upgrade(cfg, "head")` → `alembic.command.downgrade(cfg, "0011_index_ext_link_url")` → `alembic.command.upgrade(cfg, "head")` and asserts via raw `sqlite3.connect(...).execute("SELECT name FROM sqlite_master WHERE type='table'")` that `invite_tokens` is present after upgrade, absent after downgrade, present again after re-upgrade. Cite `apps/api/alembic.ini` for the `script_location` in the `Config(...)` setup.

- [x] **T2 — Author `apps/api/app/modules/invite/` package skeleton (AC-2)**
  - [x] T2.1 Create `apps/api/app/modules/invite/__init__.py` as an empty file (zero bytes; subsequent stories 6.2 / 6.3 / 6.4 add `service.py`, `router.py`, `admin_router.py`).
  - [x] T2.2 Create `apps/api/app/modules/invite/models.py` with the structure: top-of-file docstring, stdlib imports (`hashlib`, `datetime`, `uuid`, `enum.IntEnum`), SQLModel imports (`Field`, `SQLModel`), Init 0 helper imports (`from app.core.db.models._helpers import _now_utc, UTCDateTime, uuid_fk`), then class definitions in this order: `InviteTTLPreset(IntEnum)` (4 members), `InviteToken(SQLModel, table=True)` with `__tablename__ = "invite_tokens"` matching the migration's column list 1:1, then `def hash_token(token: str) -> str`.
  - [x] T2.3 `InviteToken` column definitions per spec, with one adjustment for `alembic check` parity: `token_hash` does not carry `Field(unique=True, index=True)` — instead the class declares `__table_args__ = (Index("ux_invite_tokens_token_hash", "token_hash", unique=True), Index("ix_invite_tokens_generated_at", "generated_at"), Index("ix_invite_tokens_used_by_user_id", "used_by_user_id"))`. This keeps the SQLModel metadata aligned with the migration's index names (the implicit SQLModel naming would otherwise drift to `ix_invite_tokens_token_hash` and produce `alembic check` diffs). All other columns (UUID PK, UUID FKs via `uuid_fk`, `UTCDateTime` for timestamps, `_now_utc` default, `max_length` constraints) are exactly as the spec listed.
  - [x] T2.4 `hash_token` body: `return hashlib.sha256(token.encode("utf-8")).hexdigest()`. No `bytes` overload; single-purpose stdlib wrapper. Module-private wrappers (e.g., for HMAC) are deferred — Decision B explicitly notes SHA-256 is sufficient for 256-bit opaque tokens.
  - [x] T2.5 Added `from app.modules.invite import models as _invite_models  # noqa: F401` side-effect import to `apps/api/migrations/env.py`. Verified via `alembic check` — only the pre-existing `refresh_tokens` index-naming drift remains (out of Story 6.1 scope; flagged for a future bmad-correct-course follow-up); the `invite_tokens` diff is clean.

- [x] **T3 — Extend `KNOWN_ENTITY_TYPES` + sync the test suite (AC-3)**
  - [x] T3.1 Edit `apps/api/app/core/audit.py` — added docstring entry `#   invite_token         — auth.invite.generated/used/revoked (entity_id = invite_tokens.id UUID)` and `"invite_token"` literal in alphabetical position inside the `KNOWN_ENTITY_TYPES` frozenset.
  - [x] T3.2 Edit `apps/api/tests/test_audit.py::test_known_entity_types_covers_all_call_site_resources` — added `"invite_token"` to the `expected` set; `assert expected == KNOWN_ENTITY_TYPES` now passes.
  - [x] T3.3 Added `test_record_event_accepts_invite_token_entity_type` in `apps/api/tests/test_audit.py`; verifies `record_event(engine, action="auth.invite.generated", entity_type="invite_token", entity_id=<uuid>, actor_user_id=<admin_uuid>)` persists a row with the matching pair and no `ValueError`.

- [x] **T4 — Logger `TokenRedactionFilter` + tests (AC-4)**
  - [x] T4.1 Edit `apps/api/app/core/logging.py` — added `import re`, module-level `_TOKEN_URL_REGEX = re.compile(r"\btoken=[^&\s\"']+")` + `_TOKEN_REDACTED = "token=<redacted>"`, `class TokenRedactionFilter(logging.Filter)` implementing (a) `record.msg` substitution via `str(record.msg)` cast, (b) `record.args` walk (tuple/list/dict + scalar) through `_redact_args` / `_redact_one` helpers, (c) `record.token` attribute replacement to `"<redacted>"`. `configure_logging()` now calls `handler.addFilter(TokenRedactionFilter())` before `handler.setFormatter(...)`.
  - [x] T4.2 Created `apps/api/tests/test_logging.py` with 8 tests covering all four AC-4 surfaces (URL query string, `extra={"token": ...}`, negative-path pass-through, positional `record.args`) plus three defense-in-depth checks (configure_logging wiring, non-string `msg` coercion, `record.token` attribute replacement, full-scan no-cleartext assertion). Tests use an isolated `StringIO`-backed logger so they do not perturb the global root handler.
  - [x] T4.3 Full backend pytest suite green — `apps/api/ ✓ 427 passed`. Filter is purely additive; auth/share namespaced loggers see byte-identical output for token-free records (negative-path test guards this invariant).

## Dev Notes

### Relevant architecture patterns and constraints

- **Alembic conventions** (from `apps/api/migrations/versions/0009_refresh_tokens.py` + `0011_index_ext_link_url.py`):
  - Revision id = full slug, kept ≤32 chars (Postgres `alembic_version.version_num VARCHAR(32)` constraint — explicitly cited in the `0011` module docstring as a Codex review finding on commit `7e1b026`). `"0012_invite_tokens"` is 19 chars — well within limits.
  - Imports: `from alembic import op` + `import sqlalchemy as sa`. Avoid `from sqlmodel import ...` inside migration files — migrations are SQLAlchemy-level and the SQLModel layer is reserved for application code.
  - UUID columns: `sa.Uuid(as_uuid=True)` — never `sa.String` for UUIDs. Translates to native `uuid` on Postgres + `CHAR(32)` on SQLite.
  - Datetime columns: `sa.DateTime()` (not `sa.TIMESTAMP`). The application layer wraps reads through `UTCDateTime` TypeDecorator for tz-aware Python objects; the on-disk column type stays plain DateTime.
  - Foreign keys: `sa.ForeignKey("user.id", ondelete="SET NULL")` — the User table is named `"user"` (singular), see `apps/api/app/core/db/models/_user.py` line 17 (`__tablename__ = "user"`).
  - Indexes: `op.create_index("ix_<table>_<col>", "<table>", ["<col>"], unique=<bool>)`. SQLite supports straight `op.create_index` for additive index changes without the `batch_alter_table` wrapper (per `0011`'s docstring).
  - `downgrade()` always drops indexes BEFORE the table — FK / index reference chain.

- **SQLModel conventions** (from `apps/api/app/core/db/models/_audit.py` + `_user.py` + `_helpers.py`):
  - `class X(SQLModel, table=True)` + explicit `__tablename__ = "..."`.
  - UUID PK: `id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)`.
  - UUID FK via helper: `Field(default=None, sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True))` — uses the `uuid_fk` helper from `_helpers.py` to keep every Init 0 entity FK shape consistent.
  - Timestamps: `datetime.datetime = Field(default_factory=_now_utc, sa_column=Column(UTCDateTime, nullable=...))`. The `UTCDateTime` TypeDecorator re-attaches UTC `tzinfo` on read so cross-dialect comparisons work in SQLite tests and Postgres production.
  - Composite indexes via `__table_args__ = (Index("ix_x_y", "a", "b"), ...)` — Story 6.1 only needs single-column indexes so `__table_args__` is unnecessary; the migration carries the three indexes.

- **Audit contract** (from `apps/api/app/core/audit.py` + `apps/api/tests/test_audit.py`):
  - `KNOWN_ENTITY_TYPES: frozenset[str]` holds ENTITY-TYPE strings (the resource type — `user`, `share_token`, `model`, ...), NOT action names. The docstring lines 14-26 explicitly enumerate each entity type and the actions it carries.
  - `record_event(action: str, entity_type: str, ...)` — `action` is free text (column type `TEXT` in `audit_log`), `entity_type` is closed-set-validated against `KNOWN_ENTITY_TYPES`. Unknown entity_type raises `ValueError("unknown entity_type ...")` at the helper boundary (line 65-70). The forward guard's stated purpose is to keep call-site drift from silently piling up before the planned Slice 2 enum tightening.
  - `apps/api/tests/test_audit.py::test_known_entity_types_covers_all_call_site_resources` (lines 63-79) asserts EXACT EQUALITY (`assert expected == KNOWN_ENTITY_TYPES`); any addition to the frozenset MUST be reflected in the test's `expected` set in the SAME commit, otherwise the suite fails immediately. This is the regression gate for AC-3.
  - Existing entity-type usage precedent: `record_event(action="auth.login.fail", entity_type="user", ...)` in `apps/api/app/modules/auth/router.py` line 61-68 — login/register flows use `entity_type="user"` because the action operates on the User entity, even though the action `auth.*` describes auth-domain semantics. Story 6.1 follows the same precedent: `auth.register.success` uses `entity_type="user"` (creates a User); `auth.invite.{generated,used,revoked}` uses `entity_type="invite_token"` (operates on an InviteToken entity).

- **Decision A — Invite-token dual-backed storage** (`architecture.md` § Initiative 5 Decision A, lines 1417-1423): Mirrors the Init 0 share-token pattern (`apps/api/app/modules/share/service.py`) — Redis O(1) hot path + DB row audit history. The DB row "outlives the Redis TTL" — used + expired + revoked invites remain visible in the admin panel forever; Redis only carries the active set. Story 6.1 ships the schema + primitives ONLY; the dual-write flow (Redis SET + DB INSERT) lands in Story 6.2 (`service.py`).

- **Decision B — Invite-token shape** (`architecture.md` § Initiative 5 Decision B, lines 1425-1456): 32-byte entropy via `secrets.token_urlsafe(32)` (43-char URL-safe string, 256 bits — generated in Story 6.2's `service.py`, NOT Story 6.1). Redis key `invite:token:{token}`. DB table `invite_tokens` per the column table — Drift 3 below reconciles Decision B's `INTEGER` ids with the Init 0 UUID convention. TTL preset enum `InviteTTLPreset(IntEnum)` with values `86400` / `259200` / `604800` / `2592000` lives in `apps/api/app/modules/invite/models.py`. SHA-256 (not bcrypt) for token-at-rest hashing — the rationale (256-bit search space + rate-limit middleware in Decision G yields ≥10⁶ brute-force margin per NFR5-SEC-3) is recorded verbatim in Decision B's "Rationale" paragraph.

- **Logger redaction motivation** (Decision B "Cascading" paragraph + epics.md Story 6.1 bullet #4 + prd.md NFR5-OBS-1):
  - Token NEVER logged in cleartext anywhere — query-string `token=*` values redacted, POST-body `token` field redacted.
  - Cleartext token appears only in: (1) the generated-invite admin response (one-time JSON body, never logged), (2) `/register?token=` query string during consumption (TLS-terminated at nginx; the application's structured log filter must redact before `JsonFormatter` writes the record to stdout / GlitchTip).
  - Stdlib `logging.Filter` is the right primitive (per the existing `configure_logging()` pattern in `apps/api/app/core/logging.py` lines 61-72); attach via `handler.addFilter(...)` BEFORE the formatter so the formatter sees the already-mutated record.
  - GlitchTip visibility: NFR5-OBS-1 requires `auth.register.fail` / `auth.totp.verify.fail` / `auth.login.fail` events to be counter-shaped and queryable in the GlitchTip dashboard for credential-stuffing detection. Story 6.1's filter must NOT mutate the action names, log-level, or non-token fields — only the cleartext token substring is redacted.

### Source tree components to touch

**NEW files:**

- [apps/api/migrations/versions/0012_invite_tokens.py](../../apps/api/migrations/versions/0012_invite_tokens.py) — Alembic migration.
- [apps/api/app/modules/invite/__init__.py](../../apps/api/app/modules/invite/__init__.py) — empty package stub.
- [apps/api/app/modules/invite/models.py](../../apps/api/app/modules/invite/models.py) — `InviteTTLPreset` enum + `InviteToken` SQLModel + `hash_token` helper.
- [apps/api/tests/test_migration_0012.py](../../apps/api/tests/test_migration_0012.py) — Alembic round-trip pytest.
- [apps/api/tests/test_logging.py](../../apps/api/tests/test_logging.py) — `TokenRedactionFilter` pytest (4 tests).

**UPDATE files:**

- [apps/api/app/core/audit.py](../../apps/api/app/core/audit.py) — add `"invite_token"` to `KNOWN_ENTITY_TYPES` + extend docstring catalog comment.
- [apps/api/app/core/logging.py](../../apps/api/app/core/logging.py) — add `TokenRedactionFilter` class + wire into `configure_logging()`.
- [apps/api/migrations/env.py](../../apps/api/migrations/env.py) — add `import app.modules.invite.models  # noqa: F401` so the SQLModel `InviteToken` table registers in `SQLModel.metadata` before `target_metadata` is bound.
- [apps/api/tests/test_audit.py](../../apps/api/tests/test_audit.py) — expand `expected` set in `test_known_entity_types_covers_all_call_site_resources` + optionally add `test_record_event_accepts_invite_token_entity_type` (per T3.3).

### Testing standards summary

- Framework: pytest with `asyncio_mode = "auto"`, runner `pytest-asyncio`, coverage `pytest-cov`. Story 6.1 has no async surface — pure sync stdlib + SQLModel + Alembic.
- Isolated DB: `_isolated_db` session-scope autouse fixture in [apps/api/tests/conftest.py](../../apps/api/tests/conftest.py) lines 31-57 provides a tmpdir SQLite at `os.environ["DATABASE_URL"]` + an `init_schema(get_engine())` warm-up. For T1.5 (Alembic round-trip), DO NOT reuse `_isolated_db` — the round-trip needs its own fresh tmpdir DB outside the session fixture's lifecycle so it can `upgrade` from scratch.
- Alembic round-trip pattern: `from alembic.config import Config; from alembic import command; cfg = Config("apps/api/alembic.ini"); cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'rt.db'}"); command.upgrade(cfg, "head"); command.downgrade(cfg, "0011_index_ext_link_url"); command.upgrade(cfg, "head")`. Verify table presence via raw `sqlite3.connect(...).execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invite_tokens'").fetchall()`.
- Logging tests use `caplog` fixture OR a custom `StringIO`-backed handler with `JsonFormatter` + `TokenRedactionFilter` attached. Assert via `json.loads(captured_line)["message"]` to avoid string-position fragility.
- TDD discipline (CLAUDE.md project execution discipline, AGENTS.md § "TDD for backend logic"): each acceptance criterion lands a failing test first (red), then the implementation (green), then a quick refactor pass. Order: T1 → T2 → T3 → T4, but within each task the test precedes the code change.
- `ruff format --check apps/api/` + `ruff check apps/api/` must pass before commit (`select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]`, line-length 100, py312 target).
- Full backend suite: `pytest apps/api/` (no Redis required for Story 6.1 — `_patch_arq_pool` autouse fixture covers the worker mocking).
- One-shot quality gate: `infra/scripts/check-all.sh` from repo root (added in commit `7787d52` per recent commit log).

### Project Structure Notes — drifts surfaced between binding planning artifacts and repo reality

Story 6.1 is the E6 entry story, so it is the first time the Init 5 planning chain hits actual code. Three substantive drifts + one minor naming drift surfaced during exhaustive analysis. Each is documented with (a) the drift evidence cited at file:line, (b) the code-grounded correction the Dev Agent must apply, (c) a flag for `bmad-correct-course` follow-up to clean the planning docs without changing the implementation. The drifts do NOT change Story 6.1's scope or acceptance criteria — they reconcile the binding planning text with the actual repo state.

**Drift 1 — Alembic versions path.**

- Evidence: [epics.md line 1553](../planning-artifacts/epics.md) cites `apps/api/alembic/versions/0012_invite_tokens.py`. The directory `apps/api/alembic/` does not exist (`find apps/api -maxdepth 3 -name alembic` returns nothing). The Alembic configuration at [apps/api/alembic.ini line 8](../../apps/api/alembic.ini) reads `script_location = %(here)s/migrations`, and migrations live under [apps/api/migrations/versions/](../../apps/api/migrations/versions/) (existing files `0001_initial.py` … `0011_index_ext_link_url.py`). [project-context.md line 81](../project-context.md) confirms the correct path verbatim: "Adding columns or tables = new alembic migration in `apps/api/migrations/versions/`".
- Apply correction: Story 6.1 ships the migration at `apps/api/migrations/versions/0012_invite_tokens.py`. Story 7.1 (`0013_users_2fa_columns.py`) carries the same drift — it will be corrected at its story-creation time (Sesja H+).
- Follow-up: `bmad-correct-course` patch to epics.md Stories 6.1 + 7.1 bullet #1 — single-line s/alembic\/versions/migrations\/versions/.

**Drift 2 — `KNOWN_ENTITY_TYPES` semantics: actions vs entity types.**

- Evidence: [epics.md line 1555](../planning-artifacts/epics.md) and [prd.md line 1200 FR5-AUDIT-1](../planning-artifacts/prd.md) both phrase the audit-registry expansion as "audit action names registered in KNOWN_ENTITY_TYPES" (Story 6.1's set: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`). Actual code contract at [apps/api/app/core/audit.py lines 27-42 + 65-70](../../apps/api/app/core/audit.py): `KNOWN_ENTITY_TYPES` is a `frozenset[str]` of ENTITY-TYPE values (`user`, `share_token`, `model`, ...). `record_event(action, entity_type, ...)` validates `entity_type` membership; `action` is free text passed through. Adding `"auth.invite.generated"` to `KNOWN_ENTITY_TYPES` would NOT register it as a recognised action — `record_event(action="anything", entity_type="auth.invite.generated", ...)` would be the literal observable effect, which violates the existing test `test_known_entity_types_covers_all_call_site_resources` semantics (the closed set means "what entity types may a record_event call write against", not "what actions may a record_event call emit"). Existing precedent: [apps/api/app/modules/auth/router.py line 61-68](../../apps/api/app/modules/auth/router.py) emits `record_event(action="auth.login.fail", entity_type="user", ...)` — auth-domain action, `user` entity type.
- Apply correction: Add a single new entity-type `"invite_token"` to `KNOWN_ENTITY_TYPES` (covering all three `auth.invite.*` actions, which operate on `InviteToken` entities). Reuse the existing `"user"` entity-type for `auth.register.success` (register-success creates a User row, analogous to the `auth.login.fail` → `entity_type="user"` precedent). The four action-name strings themselves are free-text values used at call sites in Stories 6.2 (`service.py` consume / revoke), 6.3 (`admin_router.py` generate / revoke), 6.4 (`auth/router.py` register flow) — no registry change is required to "make them valid". Update [apps/api/tests/test_audit.py line 63](../../apps/api/tests/test_audit.py) `expected` set to add `"invite_token"`.
- Follow-up: `bmad-correct-course` patch to epics.md Story 6.1 bullet #3 + prd.md FR5-AUDIT-1 phrasing — clarify that "16 new action names are emitted via `record_event()` against the existing 12-entry `KNOWN_ENTITY_TYPES` registry + one new entity type `invite_token` added for Story 6.1, with subsequent stories possibly adding `recovery_code` (Story 7.1) and others as their entity scopes are introduced". The wording fix is purely doc-quality; the code interpretation is settled by this story.

**Drift 3 — Decision B `INTEGER` ids + `users.id` FKs vs Init 0 UUID convention + `user` (singular) table name.**

- Evidence: [architecture.md lines 1432-1444 Decision B](../planning-artifacts/architecture.md) specifies the `invite_tokens` table with `id INTEGER PK AUTOINCREMENT`, `generated_by_user_id INTEGER NOT NULL FK users.id`, `used_by_user_id INTEGER NULL FK users.id`. The actual Init 0 `User` schema at [apps/api/app/core/db/models/_user.py lines 17-19](../../apps/api/app/core/db/models/_user.py) defines `__tablename__ = "user"` (singular) with `id: uuid.UUID` (Field default_factory=uuid.uuid4). An `INTEGER FK users.id` is doubly broken: (a) type mismatch — `INTEGER` cannot foreign-key to a `UUID`/`CHAR(32)` column, (b) table name mismatch — `users` (plural) does not exist; the table is `user` (singular). All existing entity FKs to user use the `uuid_fk("user.id", ondelete=..., nullable=...)` helper from [apps/api/app/core/db/models/_helpers.py lines 50-70](../../apps/api/app/core/db/models/_helpers.py); see precedent in `_audit.py` line 33 (`AuditLog.actor_user_id` → `uuid_fk("user.id", ondelete="SET NULL", nullable=True)`).
- Apply correction: `invite_tokens.id` is `uuid.UUID` PK via `Field(default_factory=uuid.uuid4, primary_key=True)`; both FKs to user are `uuid_fk("user.id", ondelete="SET NULL", nullable=True)` matching the `AuditLog.actor_user_id` precedent. `generated_by_user_id` is RELAXED from Decision B's `NOT NULL` to nullable, so admin row deletion preserves the audit history per the Decision A "DB row outlives the Redis TTL — used and expired invites remain visible in the admin panel forever" semantics (CASCADE on user-delete would nuke the audit history, breaking Decision A's stated property). Migration 0012 uses `sa.Uuid(as_uuid=True)` + `sa.ForeignKey("user.id", ondelete="SET NULL")` per the [0009_refresh_tokens.py lines 22-40](../../apps/api/migrations/versions/0009_refresh_tokens.py) precedent.
- Follow-up: `bmad-correct-course` patch to architecture.md Decision B column table — replace `id INTEGER PK AUTOINCREMENT` → `id UUID PK`, replace `generated_by_user_id INTEGER NOT NULL FK users.id` → `generated_by_user_id UUID NULL FK user.id ondelete=SET NULL`, replace `used_by_user_id INTEGER NULL FK users.id` → `used_by_user_id UUID NULL FK user.id ondelete=SET NULL`. Single rationale paragraph added: "All Init 0 entity FKs to user use `uuid_fk("user.id", ...)`; Decision B aligns with that convention. `generated_by_user_id` is nullable + SET NULL to preserve audit history through admin deletion per Decision A 'outlives Redis TTL' semantics."

**Drift 4 (minor, deferred) — `Role` vs `UserRole` enum naming.**

- Evidence: [architecture.md Decisions B / C / F](../planning-artifacts/architecture.md) and PRD FR5-MEMBER-* / FR5-2FA-* / FR5-CUTOVER-* use `Role.member`, `Role.admin`, `Role.agent`. Actual enum at [apps/api/app/core/db/models/_enums.py line 10](../../apps/api/app/core/db/models/_enums.py): `class UserRole(StrEnum)` with values `admin` / `agent` / `member`. The doc uses `Role` as a shorthand; the implementation uses `UserRole`.
- Apply correction: Story 6.1 needs no code-level change for this drift (the `role` column on `invite_tokens` stores the string value of a `UserRole` enum member — `StrEnum` stores as string in SQLite). Story 6.5+ Decision C work uses `UserRole.member` etc. at call sites — no `Role` import needed.
- Follow-up: optional `bmad-correct-course` patch to architecture.md s/Role\./UserRole./ globally inside the Initiative 5 section; not load-bearing for Story 6.1.

### Previous-story intelligence

E6 is the entry epic of Initiative 5 — Story 6.1 has no in-Init-5 predecessor. The nearest cross-Init cousins worth keeping in mind:

- **Init 0 share-token pattern** ([apps/api/app/modules/share/service.py](../../apps/api/app/modules/share/service.py)): Decision A explicitly mirrors this. The 6.2 service will copy the shape (Redis SET + audit row) with one inversion — share tokens TTL-expire and may be re-resolved during their TTL; invite tokens are SINGLE-USE and DEL on consume. Story 6.1 does not implement this — it ships the schema + primitives only.
- **Init 2 Story 4.4-followup retro** ([_bmad-output/implementation-artifacts/epic-4-retro-2026-05-11.md](epic-4-retro-2026-05-11.md)) — DROP `Model.legacy_id` Alembic `0010` shipped 2026-05-11; the pattern is "use `batch_alter_table` for SQLite DDL changes". Story 6.1 is purely additive (`CREATE TABLE` + `CREATE INDEX`); no `batch_alter_table` wrapping required (matches the 0009_refresh_tokens.py + 0011_index_ext_link_url.py precedent).
- **Init 3 visual-regression principle** — Story 6.1 is backend-only (no React surface), so visual-regression baselines do not apply here. Stories 6.4 + 6.5 (UI surfaces) will carry the visual-regression contract; Story 6.1 does not.

### Git intelligence summary

Most recent commits on `main` (top of `git log`):

- `bf919c2 docs(bmad): recalibrate vanilla-first subsection — single-file model + procedural drifts only` — documents the BMAD vanilla-first principle that this story spec adheres to (procedural skill discipline; no direct artifact edits; STOP on skill protest).
- `4110c31 fix(web): install in-memory localStorage shim in vitest setup` — frontend infrastructure; unrelated to Story 6.1.
- `7a73c0d docs(agents): mandate session-start bmad-help + add vanilla-first BMAD principle` — confirms the mandatory `bmad-help` discipline that gated this story-creation session.
- `eb3ee4b chore(web): orphan baseline cleanup + TB-013 close-out` — frontend cleanup; unrelated to Story 6.1.
- `7787d52 chore: add check-all.sh quality gate + opt-in pre-push hook` — adds `infra/scripts/check-all.sh` one-shot quality gate; Story 6.1's dev-story session should use this script as the final pre-commit checklist.

No backend changes in the last 5 commits — Story 6.1 lands on a stable `apps/api/` tree. The last Alembic-touching commit was `7e1b026` + `e46d47b` (TB-008 / `0011_index_ext_link_url`) on 2026-05-12 (per sprint-status.yaml comment), which set the chain target for 0012's `down_revision`.

### References

- [_bmad-output/planning-artifacts/epics.md § Initiative 5 Story 6.1](../planning-artifacts/epics.md) — lines 1545-1556. Binding scope source (4 acceptance bullets).
- [_bmad-output/planning-artifacts/architecture.md § Initiative 5 Decision A](../planning-artifacts/architecture.md) — lines 1417-1423. Dual-backed storage motivation + cascade to Decision B.
- [_bmad-output/planning-artifacts/architecture.md § Initiative 5 Decision B](../planning-artifacts/architecture.md) — lines 1425-1456. Invite-token shape (entropy + Redis key + DB schema + TTL preset enum + indexes). Drift 3 applies to id/FK type spec.
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-INVITE-1](../planning-artifacts/prd.md) — line 1167. Capability statement (256-bit entropy + dual-backed).
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-INVITE-4](../planning-artifacts/prd.md) — line 1170. Single-use replay-fails-closed semantics.
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 FR5-AUDIT-1](../planning-artifacts/prd.md) — line 1200. 16-action audit taxonomy. Drift 2 applies.
- [_bmad-output/planning-artifacts/prd.md § Initiative 5 NFR5-OBS-1](../planning-artifacts/prd.md) — line 1244. GlitchTip structured-log visibility; informs T4 logger filter wiring.
- [apps/api/migrations/versions/0009_refresh_tokens.py](../../apps/api/migrations/versions/0009_refresh_tokens.py) — Alembic `create_table` + index + UUID FK precedent.
- [apps/api/migrations/versions/0011_index_ext_link_url.py](../../apps/api/migrations/versions/0011_index_ext_link_url.py) — most recent migration; `down_revision` chain target for 0012; documents the ≤32-char revision-id constraint from Codex review on commit `7e1b026`.
- [apps/api/app/core/audit.py](../../apps/api/app/core/audit.py) — `KNOWN_ENTITY_TYPES` contract + `record_event()` `ValueError` forward guard.
- [apps/api/app/core/db/models/_audit.py](../../apps/api/app/core/db/models/_audit.py) — SQLModel `table=True` + `uuid_fk` + `Index` precedent (AuditLog).
- [apps/api/app/core/db/models/_helpers.py](../../apps/api/app/core/db/models/_helpers.py) — `uuid_fk`, `sa_uuid_type`, `UTCDateTime`, `_now_utc` shared helpers.
- [apps/api/app/core/db/models/_user.py](../../apps/api/app/core/db/models/_user.py) — User table name `"user"` (singular), UUID PK. Drift 3 evidence.
- [apps/api/app/core/db/models/_enums.py](../../apps/api/app/core/db/models/_enums.py) — `UserRole` StrEnum (`admin` / `agent` / `member`); the doc's `Role` shorthand resolves here. Drift 4 evidence.
- [apps/api/app/core/logging.py](../../apps/api/app/core/logging.py) — `JsonFormatter` shape + `configure_logging()` wiring target.
- [apps/api/app/main.py](../../apps/api/app/main.py) — `lifespan()` calls `configure_logging()` once at startup; the filter installed in `configure_logging()` is hence application-wide and effective for every namespaced logger (`app.auth.*`, `app.share.*`, future `app.invite.*` / `app.admin.invites.*`).
- [apps/api/app/modules/share/service.py](../../apps/api/app/modules/share/service.py) — Init 0 share-token Redis pattern. Decision A's mirror target. Story 6.2 implements; Story 6.1 ships only schema + primitives.
- [apps/api/app/modules/auth/router.py](../../apps/api/app/modules/auth/router.py) — existing `record_event(action="auth.login.fail", entity_type="user", ...)` precedent (Drift 2 evidence). Line 61-68.
- [apps/api/tests/conftest.py](../../apps/api/tests/conftest.py) — `_isolated_db` session fixture + env-var bootstrap pattern.
- [apps/api/tests/test_audit.py](../../apps/api/tests/test_audit.py) — `test_known_entity_types_covers_all_call_site_resources` is the exact-equality regression gate for AC-3. Lines 63-79.
- [apps/api/alembic.ini](../../apps/api/alembic.ini) — `script_location = %(here)s/migrations`. Drift 1 evidence (line 8).
- [apps/api/migrations/env.py](../../apps/api/migrations/env.py) — `target_metadata = SQLModel.metadata` + DATABASE_URL plumbing. T2.5 must add the `import app.modules.invite.models` side-effect.
- [apps/api/.../project-context.md](../project-context.md) — `apps/api/migrations/versions/` path confirmation (line 81) + Init 0 schema/auth/audit/observability rules referenced throughout this story.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) via `bmad-dev-story` skill — Sesja H, 2026-05-19.

### Debug Log References

- **TDD red→green discipline.** Each task started with a failing pytest before the implementation landed.
  - T1: `tests/test_migration_0012.py` failed with `AssertionError: assert 'invite_tokens' in {...}` after `command.upgrade(cfg, "head")` ran through 0001..0011. Green after `0012_invite_tokens.py` shipped.
  - T2: `tests/test_invite_models.py` failed at collection time with `ModuleNotFoundError: No module named 'app.modules.invite'`. Green after `invite/__init__.py` + `models.py` shipped.
  - T3: `tests/test_audit.py` showed two failures — `expected == KNOWN_ENTITY_TYPES` mismatch + `record_event` raising `ValueError("unknown entity_type 'invite_token'")`. Green after `audit.py` docstring + frozenset edits.
  - T4: `tests/test_logging.py` failed at collection time with `ImportError: cannot import name 'TokenRedactionFilter'`. Green after `logging.py` filter class + `configure_logging()` wiring.
- **Env.py override gotcha.** `apps/api/migrations/env.py` does `config.set_main_option("sqlalchemy.url", get_settings().database_url)` unconditionally, so `Config.set_main_option(...)` from the test fixture is overridden. Test fixture `_round_trip_db` now sets `DATABASE_URL` env var + clears `get_settings.cache_clear()` / `get_engine.cache_clear()` LRU caches, then restores both on teardown. The session-scope `_isolated_db` fixture's value remains intact for the rest of the suite.
- **Spec T2.3 deviation, recorded.** The spec called for `Field(unique=True, index=True)` on `token_hash`, but `alembic check` flagged an index-name drift (`ix_invite_tokens_token_hash` from SQLModel autogenerate vs `ux_invite_tokens_token_hash` from the migration). Resolved by moving all three indexes into `__table_args__` with explicit names. AC-1 + AC-2 invariants unchanged (UNIQUE on `token_hash` still enforced; unique-constraint test in `test_invite_token_hash_unique_constraint` confirms the SQLite UNIQUE index fires on duplicate inserts).
- **Pre-existing `refresh_tokens` autogenerate drift surfaced but NOT touched.** `alembic check` reports `ix_refresh_tokens_family` / `ix_refresh_tokens_user_active` removed in favour of `ix_refresh_tokens_family_id`. That diff predates Story 6.1 (0009 migration uses explicit names; SQLModel autogenerate prefers convention names). Out of scope for E6.1 — candidate for a future `bmad-correct-course` doc cleanup or a small fix-up commit during E6.2+.

### Completion Notes List

- ✅ AC-1: `alembic upgrade head` round-trip (head → -1 → head) verified via `tests/test_migration_0012.py`. The `invite_tokens` table + 3 indexes (`ux_invite_tokens_token_hash`, `ix_invite_tokens_generated_at`, `ix_invite_tokens_used_by_user_id`) appear in `sqlite_master` after upgrade, vanish after downgrade, reappear after re-upgrade. Migration is reversible and idempotent.
- ✅ AC-2: `from app.modules.invite.models import InviteTTLPreset, InviteToken, hash_token` resolves. `InviteTTLPreset` has the four spec members with values 86400 / 259200 / 604800 / 2592000. `hash_token("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"` (SHA-256 of `b"test"`). UNIQUE constraint on `token_hash` verified via `test_invite_token_hash_unique_constraint`.
- ✅ AC-3: `KNOWN_ENTITY_TYPES` now holds 13 entity types (12 + `invite_token`). `record_event(action="auth.invite.generated", entity_type="invite_token", ...)` writes a row without raising. `record_event(action="auth.register.success", entity_type="user", ...)` still works via the existing precedent. Unknown-entity guard still raises `ValueError` (negative-path test `test_record_event_rejects_unknown_entity_type` unchanged and passes).
- ✅ AC-4: `TokenRedactionFilter` substitutes `token=<value>` → `token=<redacted>` across `record.msg`, `record.args` (tuple/list/dict/scalar), and `record.token` attribute. `configure_logging()` attaches the filter before the `JsonFormatter` so the formatter always sees a sanitised record. Defense-in-depth full-scan test (`test_filter_scan_no_cleartext_leakage`) confirms `secretA/B/C` never appear in rendered output across all three surfaces.
- 🟢 Full backend pytest suite: **427 passed, 0 regressions**.
- 🟢 `ruff format --check` + `ruff check` both clean across `app/`, `tests/`, `migrations/`.
- 🟢 `infra/scripts/check-all.sh` (backend stages only — apps/web visual regression skipped per Story-6.1 backend-only scope): all 9 stages green (apps/api ruff format + check, apps/api pytest, workers/render ruff format + check, workers/render pytest, apps/web typecheck, apps/web lint, apps/web vitest).
- 📝 No new dependencies introduced. All edits live inside the existing `apps/api/` Python package; no `pyproject.toml`, no `infra/` changes, no frontend changes.
- 🔎 Drift 1-4 from spec § "Project Structure Notes" — all applied as code-level corrections in this story; doc-level `bmad-correct-course` follow-up remains optional and is NOT blocking the next stories (6.2 / 6.3 / 6.4).

### File List

**NEW (5):**

- `apps/api/migrations/versions/0012_invite_tokens.py`
- `apps/api/app/modules/invite/__init__.py`
- `apps/api/app/modules/invite/models.py`
- `apps/api/tests/test_migration_0012.py`
- `apps/api/tests/test_logging.py`
- `apps/api/tests/test_invite_models.py`

**MODIFIED (4):**

- `apps/api/app/core/audit.py` — added `"invite_token"` to `KNOWN_ENTITY_TYPES` + docstring entry.
- `apps/api/app/core/logging.py` — added `TokenRedactionFilter` + module-level regex + wiring in `configure_logging`.
- `apps/api/migrations/env.py` — added `app.modules.invite.models` side-effect import.
- `apps/api/tests/test_audit.py` — expanded `expected` set + added `test_record_event_accepts_invite_token_entity_type`.

**SPRINT STATE (1):**

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — flipped `6-1-alembic-0012-invite-tokens-primitives` `ready-for-dev` → `in-progress` → `review`.

### Change Log

- **2026-05-19 — Story 6.1 implementation (Sesja H).** Shipped Alembic migration `0012_invite_tokens` (table + 3 indexes, UUID PK/FKs, nullable FKs via `SET NULL` to preserve audit history through admin deletion). Shipped `apps/api/app/modules/invite/` package skeleton with `InviteTTLPreset(IntEnum)`, `InviteToken(SQLModel)`, and `hash_token()` SHA-256 helper. Extended `KNOWN_ENTITY_TYPES` audit registry with `invite_token`. Added `TokenRedactionFilter` to the structured-log pipeline so cleartext invite tokens never reach stdout / GlitchTip. All 4 ACs satisfied; 427 backend tests green; ruff clean; pre-existing `refresh_tokens` autogenerate drift documented but not in-scope.
