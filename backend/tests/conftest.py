import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from app.main import app
from app.middleware.rate_limit import limiter


@pytest.fixture
def client() -> TestClient:
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    limiter.reset()


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@ember.dev"


@pytest.fixture
def registered_user(client: TestClient, unique_email: str) -> dict[str, str]:
    password = "correct-horse"
    response = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": password, "display_name": "Ada"},
    )
    assert response.status_code == 201, response.text
    return {"email": unique_email, "password": password}


@pytest.fixture(autouse=True)
def _cleanup_test_users(unique_email: str):
    yield
    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM users WHERE email = :email"),
            {"email": unique_email},
        )
        db.commit()
    finally:
        db.close()
