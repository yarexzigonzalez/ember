from fastapi.testclient import TestClient


def test_register_keeps_browser_timezone(client: TestClient, unique_email: str) -> None:
    created = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "long-enough", "timezone": "Asia/Tokyo"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["timezone"] == "Asia/Tokyo"


def test_register_rejects_made_up_timezone(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "long-enough", "timezone": "GMT+99"},
    )
    assert response.status_code == 422


def test_missing_timezone_defaults_to_utc(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    assert client.get("/api/auth/me").json()["timezone"] == "UTC"


def test_patch_settings(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    changed = client.patch(
        "/api/auth/me",
        json={"timezone": "America/New_York", "weekly_goal": 5, "ghost_after_days": 10},
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert (body["timezone"], body["weekly_goal"], body["ghost_after_days"]) == (
        "America/New_York",
        5,
        10,
    )
    assert client.patch("/api/auth/me", json={"timezone": "Nope/Nope"}).status_code == 422
    assert client.patch("/api/auth/me", json={"weekly_goal": 0}).status_code == 422
