from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal


def _login(client: TestClient, user: dict[str, str]) -> None:
    response = client.post("/auth/login", json=user)
    assert response.status_code == 200


def test_crud_and_status_history(client: TestClient, registered_user: dict[str, str]) -> None:
    _login(client, registered_user)
    created = client.post(
        "/applications",
        json={
            "company": "Stripe",
            "role": "Backend Intern",
            "source": "LinkedIn",
            "posting_url": "https://stripe.com/jobs/1",
            "status": "applied",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "applied"
    assert body["applied_at"] is not None
    app_id = body["id"]

    listed = client.get("/applications")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    moved = client.patch(f"/applications/{app_id}", json={"status": "oa"})
    assert moved.status_code == 200
    assert moved.json()["status"] == "oa"

    gone = client.delete(f"/applications/{app_id}")
    assert gone.status_code == 204
    assert client.get(f"/applications/{app_id}").status_code == 404


def test_duplicate_company_role_link(client: TestClient, registered_user: dict[str, str]) -> None:
    _login(client, registered_user)
    payload = {
        "company": "Notion",
        "role": "New Grad",
        "posting_url": "https://notion.so/jobs/2",
    }
    assert client.post("/applications", json=payload).status_code == 201
    again = client.post("/applications", json={**payload, "company": " notion "})
    assert again.status_code == 409


def test_other_user_cannot_see_rows(
    client: TestClient, registered_user: dict[str, str], unique_email: str
) -> None:
    _login(client, registered_user)
    created = client.post(
        "/applications",
        json={"company": "Figma", "role": "Intern", "posting_url": "https://figma.com/j"},
    )
    assert created.status_code == 201
    app_id = created.json()["id"]
    assert client.post("/auth/logout").status_code == 204

    other = client.post(
        "/auth/register",
        json={"email": f"other-{unique_email}", "password": "another-password"},
    )
    assert other.status_code == 201
    assert (
        client.post(
            "/auth/login",
            json={"email": f"other-{unique_email}", "password": "another-password"},
        ).status_code
        == 200
    )
    assert client.get("/applications").json()["total"] == 0
    assert client.get(f"/applications/{app_id}").status_code == 404
    assert client.patch(f"/applications/{app_id}", json={"status": "offer"}).status_code == 404
    client.post("/auth/logout")
    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM users WHERE email = :email"),
            {"email": f"other-{unique_email}"},
        )
        db.commit()
    finally:
        db.close()


def test_search_filter_and_sort(client: TestClient, registered_user: dict[str, str]) -> None:
    _login(client, registered_user)
    rows = [
        {"company": "Stripe", "role": "Backend Intern", "source": "LinkedIn", "status": "applied"},
        {"company": "Airbnb", "role": "iOS Intern", "source": "Referral", "status": "saved"},
        {"company": "Stripe", "role": "Data Intern", "source": "Handshake", "status": "saved"},
    ]
    for row in rows:
        assert client.post("/applications", json=row).status_code == 201

    found = client.get("/applications", params={"q": "stripe", "sort": "role", "direction": "asc"})
    assert found.status_code == 200
    payload = found.json()
    assert payload["total"] == 2
    assert [item["role"] for item in payload["items"]] == ["Backend Intern", "Data Intern"]

    saved = client.get("/applications", params={"status": "saved", "source": "Referral"})
    assert saved.json()["total"] == 1
    assert saved.json()["items"][0]["company"] == "Airbnb"


def test_applications_require_login(client: TestClient) -> None:
    assert client.get("/applications").status_code == 401
