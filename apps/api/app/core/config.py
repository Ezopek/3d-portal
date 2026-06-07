from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.db.models._enums import UserRole


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "3d-portal-api"
    app_version: str = "0.1.0"
    environment: str = Field(default="dev")  # "dev" | "production"

    # Volumes (paths inside container)
    catalog_data_dir: Path = Path("/data/catalog")
    renders_dir: Path = Path("/data/renders")
    state_dir: Path = Path("/data/state")
    catalog_cache_dir: Path = Path("/data/cache")
    portal_content_dir: Path = Path("/data/content")  # SoT binary storage (Slice 2B+)

    # DB
    database_url: str = "sqlite:////data/state/portal.db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 10
    cookie_secure: bool = True
    admin_email: str = "admin@local"
    admin_password: str = "change-me"
    totp_fernet_key: str = ""

    # 2FA enforcement (Story 7.4, Decision F)
    enforce_2fa_for_roles: Annotated[list[UserRole], NoDecode] = Field(default_factory=list)

    # Rate-limiting (Story 6.6, Decision G)
    ratelimit_login_window_seconds: int = 60
    ratelimit_login_threshold: int = 5
    ratelimit_refresh_window_seconds: int = 60
    ratelimit_refresh_threshold: int = 10
    ratelimit_register_window_seconds: int = 60
    ratelimit_register_threshold: int = 3
    # Rate-limiting (Story 6.7, Decision H — per-member share cap)
    ratelimit_share_window_seconds: int = 86400
    ratelimit_share_threshold: int = 20
    ratelimit_share_soft_alert_threshold: int = 10
    # Rate-limiting (Story 19.1, Decision Q — anonymous share view DDoS cap)
    # Operator-calibrated 2026-05-23 via Init 12 AskUserQuestion.
    ratelimit_share_anon_window_seconds: int = 60
    ratelimit_share_anon_threshold: int = 60  # 1 req/sec rolling per (token, IP)
    ratelimit_share_anon_soft_alert_threshold: int = 30
    # Rate-limiting (Story 23.3, Decision Y — per-token share view DDoS cap)
    # Operator-calibrated 2026-05-24 via Init 16 AskUserQuestion. Layered on top
    # of the per-(token, IP) cap above: binds total req volume per token regardless
    # of source IP, so a botnet wielding a leaked token cannot defeat the per-IP
    # cap by distributing across many IPs. FR16-RATELIMIT-PER-TOKEN-1.
    ratelimit_share_per_token_window_seconds: int = Field(default=60, ge=10, le=3600)
    ratelimit_share_per_token_threshold: int = Field(default=60, ge=1, le=100000)
    # Soft-alert threshold is OPTIONAL (default disabled). Empty-string env var
    # (compose forwarding `${VAR:-}` when unset by operator) coerces to None via
    # the field_validator below — without it, pydantic would reject "" for int.
    ratelimit_share_per_token_soft_alert_threshold: int | None = Field(
        default=None, ge=1, le=100000
    )

    @field_validator("ratelimit_share_per_token_soft_alert_threshold", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        """Coerce empty-string env-var to None for the optional soft-alert field.

        ``${RATELIMIT_SHARE_PER_TOKEN_SOFT_ALERT_THRESHOLD:-}`` in docker-compose
        produces an empty string when the operator has not set the env var.
        Pydantic would otherwise reject "" for an int|None field at startup-
        config-load, breaking the "default disabled" contract from the spec.
        """
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    # Story 8.5: admin-issued password-reset link TTL bounds.
    password_reset_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    # Initiative 19 Story 31.1 (Decision AE) — Spoolman integration.
    # Primary topology P4b: portal-api joins the same docker network as
    # Spoolman and resolves ``http://spoolman:8000``. Operator fallback P4a:
    # set ``SPOOLMAN_URL=http://localhost:7912`` if the configs-side compose
    # PR attaching Spoolman to ``portal-network`` has not yet shipped.
    spoolman_url: str = "http://spoolman:8000"
    # Reserved for future P3d Spoolman auth (Phase C trigger; per operator
    # decision 4, NOT triggered by MVP-A). Carried in MVP-A so the
    # ``Authorization: Bearer …`` wiring lands once and the env-driven swap
    # stays a one-file change. Empty value disables the header.
    spoolman_auth_token: str = ""

    # Slicer (Initiative 20, Story 32.1) — Orca profile-resolver slots.
    # orca_version is sourced from ORCA_VERSION and folded into bundle_hash
    # because "an Orca upgrade is a clean bulk-invalidation event — Decision AJ /
    # NFR20-REPRODUCIBLE-1" (AC-10). Pinned to the verified Linux AppImage build
    # (Decision AI) so it is never silently empty in the hash input.
    orca_version: str = "2.3.2"
    # Vendored Orca system-profile tree + user partials — exported artifacts (a
    # one-time bench snapshot), read at resolve time. NEVER a live read of an
    # external bench/Windows host (Decision AH § 1; AC-2/AC-12). Container-internal
    # path under the portal-content volume by default; the bench export step
    # (FENRIR_EXPORT_PATH, see infra/env.example) is NOT a production runtime path.
    slicer_vendored_profiles_dir: Path = Path("/data/content/slicer/vendored")
    # Append-only on-disk bundle + snapshot store ROOT (AC-6); hash-fanout layout on
    # the portal-content volume — NOT an Alembic table (SCP: "No DB schema"). This is
    # the store ROOT: BundleStore adds the internal ``bundles/`` and ``snapshots/``
    # children itself, so the default is ``/data/content/slicer`` (NOT
    # ``…/slicer/bundles``, which would nest to ``…/slicer/bundles/bundles/…``).
    slicer_bundle_store_dir: Path = Path("/data/content/slicer")
    # Append-only estimate cache ROOT (Story 32.3, AC-9; Decision AJ) — hash-fanout JSON
    # store on the portal-content volume, NOT an Alembic table (SCP: "No DB schema;
    # append-only estimate records"). This is the store ROOT: EstimateStore adds the
    # internal ``estimates/`` child + the <stl_hash[:2]>/<stl_hash>/<bundle_hash>.json
    # key layout itself, so the default is ``/data/content/slicer`` (NOT
    # ``…/slicer/estimates``, which would nest to ``…/estimates/estimates/…`` — the Story
    # 32.1 review-fix-5 double-nest trap). Container-internal path, never an external-host one.
    slicer_estimate_store_dir: Path = Path("/data/content/slicer")
    # Portal-owned profile-selection policy store ROOT (Story 35.1, Init 23 / Decision AS).
    # A single ``profile_policy.json`` (material defaults + per-Spoolman-filament Orca
    # filament-profile overrides) on the portal-content volume — NOT an Alembic table (SCP
    # 2026-06-07: "portal-owned small JSON store first, not a DB migration").
    # ProfilePolicyStore adds the ``profile_policy.json`` filename itself, so the default
    # is the ``/data/content/slicer`` root. Container-internal path, never an external-host
    # one; read on demand (mtime-cached),
    # so a policy edit needs no restart.
    slicer_profile_policy_dir: Path = Path("/data/content/slicer")

    # Slicer worker (Initiative 20, Story 32.2, Decision AI) — headless Orca CLI
    # invoke + classify slots. Production runtime home for these is the configs-side
    # slicer-worker container (AC-12), which shares the api image and therefore loads
    # the same Settings; the api/arq-worker containers carry the same defaults so the
    # settings-env-compose drift gate stays aligned (the value there is inert — only
    # the slicer-worker actually spawns Orca).
    #
    # slicer_orca_bin: the Orca entrypoint, read from a settings slot, NEVER a literal
    # — because "the --appimage-extract entrypoint inside the configs-side slicer-worker
    # container — NFR20-CONTAINER-1; MUST NOT be a bench/external-host/binary literal"
    # (AC-10). The configs recipe sets ORCA_BIN (AC-12); SLICER_ORCA_BIN is the
    # name-aligned var the drift gate expects — AliasChoices accepts either, ORCA_BIN
    # winning so the container's value applies.
    slicer_orca_bin: str = Field(
        default="/opt/orca/orca",
        validation_alias=AliasChoices("ORCA_BIN", "SLICER_ORCA_BIN"),
    )
    # slicer_stl_cache_dir: content-hash STL cache root (AC-4); fan-out layout
    # <root>/stl/<hash[:2]>/<hash>.stl. Populated API-side at enqueue from the
    # .190-mirrored catalog copy; the worker only ever reads this cache (OD-8).
    slicer_stl_cache_dir: Path = Path("/data/content/slicer/stl-cache")
    # slicer_max_concurrency: arq max_jobs cap default 1 — because "small bounded cap
    # so a minutes-long slice can't starve API/render workers on .190 — NFR20-RESOURCE-1
    # / OD-6" (AC-10). Configurable up to 2 if .190 headroom allows.
    slicer_max_concurrency: int = Field(default=1, ge=1, le=4)
    # slicer_slice_timeout_seconds: wall-time ceiling on the slice subprocess — because
    # "ARBITRARY conservative safety ceiling on slice WALL-TIME (not print time) —
    # replace once the configs-side R3 container spike benchmarks real slice wall-time;
    # NOT a contractual value (avoids the TB-016 anti-pattern)" (AC-10).
    slicer_slice_timeout_seconds: int = Field(default=900, ge=1)
    # slicer_info_timeout_seconds: short ceiling on the cheap --info pre-check — because
    # "ARBITRARY short ceiling on the cheap --info pre-check — replace at benchmark; the
    # pre-check is sub-slice fast by design" (AC-10).
    slicer_info_timeout_seconds: int = Field(default=60, ge=1)

    # Catalog-STL estimate ingestion (EST-INGEST-1) — the single configurable default
    # print-intent preset the ingestion service resolves + slices for each catalog STL
    # part. Typed as plain str here (no slicer-module import into core config); the
    # PrintIntentPreset construction validates material_class/quality_tier against their
    # Literal sets at the seam, so a bad env value fails loud, not silently.
    #
    # PLA / standard pin the bundle the shipped FilesTab UX default bar ("PLA · Standard")
    # reads on first load — the first slice MUST populate that exact bundle or the
    # default-load chip is permanently ``absent`` (see _bmad-output/ux/…-files-ux.md).
    slicer_default_material_class: str = "PLA"
    slicer_default_quality_tier: str = "standard"
    # ARBITRARY-until-multi-printer: the homelab printer identity used as THE printer
    # across the Epic 32 test suite. Env-overridable; resolve fails LOUD + classified if
    # no vendored profile matches. Replace when a printer registry / per-model printer
    # selection lands. Operator owns confirming a vendored profile for
    # (this printer, PLA, standard) exists on .190 (see EST-INGEST-1 runtime gate).
    slicer_default_printer_ref: str = "creality-k1-max-microswiss-hf"

    # Observability
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None  # e.g. "authorization=Bearer <token>"

    # Error tracking (GlitchTip / Sentry SDK)
    sentry_dsn: str | None = None
    portal_version: str = "0.1.0"

    # Print-ready file extensions used by the bundle download endpoint.
    # Configurable via DOWNLOAD_EXTENSIONS env var as a comma-separated list
    # (with or without leading dots), e.g. "stl,3mf,obj".
    download_extensions: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [".stl", ".3mf", ".obj", ".step", ".gcode", ".amf"]
    )

    @field_validator("download_extensions", mode="before")
    @classmethod
    def _parse_extensions(cls, v: object) -> object:
        if isinstance(v, str):
            v = [item for item in v.split(",")]
        if isinstance(v, list):
            normalized = []
            for item in v:
                if not isinstance(item, str):
                    continue
                ext = item.strip().lower()
                if not ext:
                    continue
                if not ext.startswith("."):
                    ext = "." + ext
                normalized.append(ext)
            return normalized
        return v

    @field_validator("enforce_2fa_for_roles", mode="before")
    @classmethod
    def _parse_roles(cls, v: object) -> object:
        if isinstance(v, str):
            v = [item for item in v.split(",")]
        if isinstance(v, list):
            normalized: list[UserRole] = []
            for item in v:
                if isinstance(item, UserRole):
                    normalized.append(item)
                    continue
                if not isinstance(item, str):
                    continue
                candidate = item.strip().lower()
                if not candidate:
                    continue
                try:
                    normalized.append(UserRole(candidate))
                except ValueError as exc:
                    raise ValueError(
                        f"enforce_2fa_for_roles contains unknown role "
                        f"{item!r}; valid roles are: {', '.join(r.value for r in UserRole)}"
                    ) from exc
            return normalized
        return v

    @property
    def sqlite_path(self) -> Path | None:
        # SQLite URLs use 3 slashes for relative paths (sqlite:///portal.db -> portal.db)
        # and 4 for absolute (sqlite:////data/state/portal.db -> /data/state/portal.db).
        # Stripping a 3-slash prefix preserves the leading `/` of absolute paths.
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url.removeprefix("sqlite:///"))
        return None

    @model_validator(mode="after")
    def _block_default_secrets_in_prod(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret == "change-me-in-production":
                raise ValueError(
                    "jwt_secret must be set to a real value in production; "
                    "the default placeholder is not allowed."
                )
            if self.admin_password == "change-me":
                raise ValueError(
                    "admin_password must be set to a real value in production; "
                    "the default placeholder is not allowed."
                )
            # NOTE: Story 7.1 originally fail-fast on missing key in production.
            # Relaxed 2026-05-19 (production incident response): Story 7.1 only
            # adds schema columns and audit registry entries — no encryption ops
            # run until Story 7.2 ships the enrollment endpoint. Re-tighten this
            # gate in Story 7.2 where the key is first actually consumed.
            if not self.totp_fernet_key:
                import warnings

                warnings.warn(
                    "TOTP_FERNET_KEY is unset in production — Story 7.2 enrollment "
                    "endpoint will fail until this is provisioned. Generate one "
                    'with: python -c "from cryptography.fernet import Fernet; '
                    'print(Fernet.generate_key().decode())"',
                    stacklevel=2,
                )
        # Shape-validate whenever a key is provided so a malformed value fails
        # fast at startup, not later when the first 2FA enrollment attempts to
        # encrypt a TOTP secret (cryptography.fernet.Fernet rejects bad keys at
        # construction).
        if self.totp_fernet_key:
            from cryptography.fernet import Fernet

            try:
                Fernet(self.totp_fernet_key.encode())
            except (ValueError, TypeError) as e:
                raise ValueError(
                    "TOTP_FERNET_KEY must be a valid Fernet key "
                    f"(url-safe base64-encoded 32-byte key): {e}"
                ) from e
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
