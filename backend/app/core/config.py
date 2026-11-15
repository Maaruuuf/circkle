from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Application settings, loaded from environment variables (and .env locally)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    app_name: str = "Circkle"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = False
    sentry_dsn: str = ""

    # --- Required secrets: no defaults on purpose, the app must fail fast ---
    database_url: str
    jwt_secret_key: SecretStr

    # --- Database / Redis ---------------------------------------------------
    db_pool_size: int = 5
    db_max_overflow: int = 10
    redis_url: str = ""  # empty -> in-memory fallback (single process only)

    # --- Web / security -----------------------------------------------------
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    trusted_proxy: bool = False  # trust X-Real-IP set by our own reverse proxy
    cookie_secure: bool = True
    cookie_domain: str = ""
    rate_limit_enabled: bool = True

    # --- Auth ----------------------------------------------------------------
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_reuse_grace_seconds: int = 10
    email_verify_expire_hours: int = 24
    password_reset_expire_minutes: int = 30
    require_email_verification: bool = False

    # --- Google OAuth (optional) ----------------------------------------------
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_redirect_uri: str = "http://localhost:3000/api/v1/auth/google/callback"

    # --- Email -----------------------------------------------------------------
    email_backend: Literal["console", "smtp", "memory"] = "console"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = True
    smtp_from: str = "Circkle <no-reply@circkle.local>"

    # --- Media -------------------------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    media_root: str = "media_files"
    media_public_base_url: str = ""  # CDN / bucket URL; empty -> serve from /media
    max_upload_mb: int = 5
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "auto"
    s3_access_key_id: str = ""
    s3_secret_access_key: SecretStr = SecretStr("")

    # --- Webhooks (outgoing) -----------------------------------------------------
    webhook_url: str = ""
    webhook_secret: SecretStr = SecretStr("")

    @field_validator("jwt_secret_key")
    @classmethod
    def secret_key_must_be_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"JWT secret key must be at least {MIN_SECRET_KEY_LENGTH} characters"
            )
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.environment != "production":
            return self
        problems: list[str] = []
        if self.debug:
            problems.append("DEBUG must be false")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true")
        if "*" in self.cors_origin_list:
            problems.append("CORS_ORIGINS must not contain '*'")
        if self.email_backend == "memory":
            problems.append("EMAIL_BACKEND must not be 'memory'")
        if self.storage_backend == "s3" and not self.s3_bucket:
            problems.append("S3_BUCKET is required when STORAGE_BACKEND=s3")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_origins(self) -> set[str]:
        """Origins allowed to send cookie-authenticated, state-changing requests."""
        return {*self.cors_origin_list, self.frontend_url.rstrip("/")}

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret.get_secret_value())

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
