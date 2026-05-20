from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
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
    # Story 8.5: admin-issued password-reset link TTL bounds.
    password_reset_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

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
