from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config from environment variables (and an optional .env file)."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://ember:ember@localhost:5433/ember"
    environment: str = "development"

    # Only matters if something calls the API cross-origin. In prod the browser
    # talks to Vercel and Vercel proxies /api/*, so it's all same-origin and this
    # can stay empty.
    cors_origins: str = ""

    cookie_name: str = "ember_session"
    cookie_secure: bool = False
    session_ttl_seconds: int = 60 * 60 * 24 * 14  # 14 days

    auth_rate_limit: int = Field(default=10, ge=1)
    auth_rate_window_seconds: int = Field(default=15 * 60, ge=1)

    # How many proxies sit in front of the app and append to X-Forwarded-For.
    # 0 locally (uvicorn sees your real IP). Vercel -> Render is 2.
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)
    # Flip on for a bit after deploy to see what IP the limiter actually uses.
    log_client_ip: bool = False

    # Quick Add. No key = heuristic only, which works fine, just dumber.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    anthropic_timeout_seconds: float = 20.0
    extract_rate_limit: int = Field(default=20, ge=1)
    extract_rate_window_seconds: int = Field(default=10 * 60, ge=1)

    @field_validator("database_url")
    @classmethod
    def use_psycopg3(cls, value: str) -> str:
        """Render (and most hosts) hand out postgres:// or postgresql:// URLs.
        SQLAlchemy needs to be told to use psycopg 3, so swap the scheme."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_for_environment(self) -> None:
        if "*" in self.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS can't be * when cookies are involved")
        if self.is_production and not self.cookie_secure:
            raise RuntimeError("COOKIE_SECURE has to be true in production")


settings = Settings()
