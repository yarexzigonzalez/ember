from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.rate_limit import limiter


def test_register_then_login_sets_httponly_cookie(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    login = client.post("/auth/login", json=registered_user)
    assert login.status_code == 200
    cookie = login.cookies.get(settings.cookie_name)
    assert cookie
    set_cookie = login.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert settings.cookie_name in set_cookie

    me = client.get("/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == registered_user["email"]
    assert body["display_name"] == "Ada"
    assert "password_hash" not in body


def test_duplicate_register_conflict(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    again = client.post(
        "/auth/register",
        json={"email": registered_user["email"], "password": "another-ok"},
    )
    assert again.status_code == 409


def test_short_password_rejected(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/auth/register",
        json={"email": unique_email, "password": "short"},
    )
    assert response.status_code == 422


def test_bad_password_is_401(client: TestClient, registered_user: dict[str, str]) -> None:
    response = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_unknown_email_is_same_401(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "nobody@ember.dev", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_logout_clears_session(client: TestClient, registered_user: dict[str, str]) -> None:
    assert client.post("/auth/login", json=registered_user).status_code == 200
    assert client.get("/auth/me").status_code == 200
    logout = client.post("/auth/logout")
    assert logout.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_me_without_cookie_is_401(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_auth_rate_limit_trips(client: TestClient, unique_email: str) -> None:
    limiter.reset()
    original_limit = settings.auth_rate_limit
    settings.auth_rate_limit = 3
    try:
        payload = {"email": unique_email, "password": "a-long-enough"}
        statuses = [
            client.post("/auth/register", json=payload).status_code for _ in range(4)
        ]
    finally:
        settings.auth_rate_limit = original_limit
        limiter.reset()
    assert 429 in statuses
