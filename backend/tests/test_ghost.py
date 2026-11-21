from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.helpers import backdate


def _add(client: TestClient, company: str, status: str) -> str:
    response = client.post(
        "/api/applications", json={"company": company, "role": "SWE Intern", "status": status}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_quiet_open_jobs_show_up(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    old_applied = _add(client, "Quiet Co", "applied")
    old_rejected = _add(client, "Closed Co", "rejected")
    _add(client, "Fresh Co", "applied")
    now = datetime.now(UTC)
    backdate(old_applied, now - timedelta(days=20))
    backdate(old_rejected, now - timedelta(days=40))

    body = client.get("/api/ghost").json()
    assert body["after_days"] == 14
    assert [item["application"]["company"] for item in body["items"]] == ["Quiet Co"]
    assert body["items"][0]["days_quiet"] == 20
    # Radar only flags it. Status is untouched.
    assert body["items"][0]["application"]["status"] == "applied"


def test_threshold_follows_user_setting(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    app_id = _add(client, "Medium Quiet", "interview")
    backdate(app_id, datetime.now(UTC) - timedelta(days=8))
    assert client.get("/api/ghost").json()["items"] == []
    client.patch("/api/auth/me", json={"ghost_after_days": 7})
    assert len(client.get("/api/ghost").json()["items"]) == 1


def test_draft_works_without_a_key(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    app_id = _add(client, "Draft Co", "oa")
    draft = client.post(f"/api/ghost/{app_id}/draft")
    assert draft.status_code == 200
    body = draft.json()
    assert body["via"] == "template"
    assert "Draft Co" in body["text"] and "online assessment" in body["text"]
