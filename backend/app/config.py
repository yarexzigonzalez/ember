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

    cors_origins: str = "http://localhost:5173"

    cookie_name: str = "ember_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    session_ttl_seconds: int = 60 * 60 * 24 * 14  # 14 days

    auth_rate_limit: int = Field(default=10, ge=1)
    auth_rate_window_seconds: int = Field(default=15 * 60, ge=1)

    @field_validator("cookie_samesite")
    @classmethod
    def samesite_must_be_known(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_for_environment(self) -> None:
        if self.environment != "production":
            return
        origins = self.cors_origin_list
        if not origins or "*" in origins:
            raise RuntimeError("CORS_ORIGINS must be an explicit list in production (no *)")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise RuntimeError("COOKIE_SECURE must be true when COOKIE_SAMESITE=none")


settings = Settings()
