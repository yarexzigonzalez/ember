import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "raw",
    [
        "postgres://u:p@host:5432/db",
        "postgresql://u:p@host:5432/db",
        "postgresql+psycopg://u:p@host:5432/db",
    ],
)
def test_database_url_always_uses_psycopg3(raw: str) -> None:
    assert Settings(database_url=raw).database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_production_refuses_insecure_cookie() -> None:
    with pytest.raises(RuntimeError):
        Settings(environment="production", cookie_secure=False).validate_for_environment()
    Settings(environment="production", cookie_secure=True).validate_for_environment()


def test_wildcard_cors_is_refused() -> None:
    with pytest.raises(RuntimeError):
        Settings(cors_origins="*").validate_for_environment()
