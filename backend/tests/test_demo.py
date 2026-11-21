import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.extract import get_llm
from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.middleware.rate_limit import limiter
from app.models.application import Application
from app.services import demo as demo_module
from app.services.demo import DEMO_ROWS, reset_demo
from app.services.extract.protocol import ExtractedJob


@pytest.fixture
def demo_client(client: TestClient) -> TestClient:
    db = SessionLocal()
    reset_demo(db)
    db.close()
    response = client.post("/api/auth/demo")
    assert response.status_code == 200, response.text
    return client


def test_reset_is_repeatable() -> None:
    db = SessionLocal()
    try:
        first = reset_demo(db)
        second = reset_demo(db)
        assert first.id == second.id
        count = db.scalar(select(func.count()).where(Application.user_id == second.id))
        assert count == DEMO_ROWS
        assert second.is_demo and second.timezone == "America/Los_Angeles"
    finally:
        db.close()


def test_one_click_session(demo_client: TestClient) -> None:
    me = demo_client.get("/api/auth/me").json()
    assert me["is_demo"] is True
    pulse = demo_client.get("/api/analytics/pulse").json()
    assert pulse["applied"] > 50  # charts actually have something in them


def test_demo_cookie_is_short_lived(client: TestClient) -> None:
    db = SessionLocal()
    reset_demo(db)
    db.close()
    set_cookie = client.post("/api/auth/demo").headers["set-cookie"].lower()
    assert "max-age=14400" in set_cookie and "samesite=lax" in set_cookie


def test_demo_can_use_the_board_but_not_settings(demo_client: TestClient) -> None:
    row = demo_client.get("/api/applications", params={"status": "applied"}).json()["items"][0]
    moved = demo_client.patch(f"/api/applications/{row['id']}", json={"status": "interview"})
    assert moved.status_code == 200
    assert demo_client.patch("/api/auth/me", json={"timezone": "UTC"}).status_code == 403
    assert demo_client.patch("/api/auth/me", json={"weekly_goal": 1}).status_code == 403


def test_demo_import_is_capped(demo_client: TestClient) -> None:
    big = "company,role\n" + "".join(f"Co{i},Role{i}\n" for i in range(30))
    assert demo_client.post("/api/import", json={"csv": big}).status_code == 400
    small = "company,role\n" + "".join(f"Small{i},Role{i}\n" for i in range(5))
    assert demo_client.post("/api/import", json={"csv": small}).json()["added"] == 5


def test_demo_board_cap(demo_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(demo_module, "DEMO_MAX_ROWS", DEMO_ROWS)
    response = demo_client.post("/api/applications", json={"company": "X", "role": "Y"})
    assert response.status_code == 403


class ExpensiveLlm:
    name = "should-not-run"

    def extract(self, text: str) -> ExtractedJob:
        raise AssertionError("demo users must never hit the paid model")


def test_demo_never_bills_the_llm(demo_client: TestClient) -> None:
    app.dependency_overrides[get_llm] = lambda: ExpensiveLlm()
    try:
        body = demo_client.post(
            "/api/extract", json={"text": "Software Engineer Intern at Stripe. Remote."}
        ).json()
    finally:
        app.dependency_overrides.clear()
    assert body["via"] == "heuristic"


def test_demo_endpoint_shares_the_auth_limiter(client: TestClient) -> None:
    original = settings.auth_rate_limit
    settings.auth_rate_limit = 2
    limiter.reset()
    try:
        codes = [client.post("/api/auth/demo").status_code for _ in range(3)]
    finally:
        settings.auth_rate_limit = original
        limiter.reset()
    assert codes[-1] == 429
