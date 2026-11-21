"""Hand-built rows with numbers you can check on a calculator."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal


def _set_event_time(app_id: str, to_status: str, when: datetime) -> None:
    db = SessionLocal()
    db.execute(
        text(
            "UPDATE status_events SET occurred_at = :w WHERE application_id = :a AND to_status = :s"
        ),
        {"w": when, "a": app_id, "s": to_status},
    )
    db.commit()
    db.close()


def test_pulse_numbers(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)

    def add(company, source, role_type, applied_at, moves=()):
        body = {
            "company": company,
            "role": "Eng",
            "source": source,
            "role_type": role_type,
            "status": "applied" if applied_at else "saved",
            "applied_at": applied_at,
        }
        app_id = client.post("/api/applications", json=body).json()["id"]
        for status, when in moves:
            client.patch(f"/api/applications/{app_id}", json={"status": status})
            _set_event_time(app_id, status, when)
        return app_id

    # Mon 2026-11-02 applies
    add("A", "LinkedIn", "intern", "2026-11-02", [("oa", datetime(2026, 11, 6, 18, tzinfo=UTC))])
    add("B", "LinkedIn", "intern", "2026-11-02", [("ghosted", datetime(2026, 11, 20, tzinfo=UTC))])
    # Wed 2026-11-04
    add(
        "C",
        "Referral",
        "full_time",
        "2026-11-04",
        [
            ("interview", datetime(2026, 11, 6, tzinfo=UTC)),
            ("rejected", datetime(2026, 11, 12, tzinfo=UTC)),  # second response, ignored
        ],
    )
    add(
        "D",
        "Referral",
        "full_time",
        "2026-11-04",
        [("rejected", datetime(2026, 11, 14, tzinfo=UTC))],
    )
    add("E", None, None, None)  # saved: not in any denominator

    body = client.get("/api/analytics/pulse").json()
    assert body["applied"] == 4
    assert body["responded"] == 3  # A (oa), C, D. ghosted doesn't count.
    assert body["response_rate"] == 0.75
    # waits: A 4d, C 2d, D 10d -> median 4
    assert body["median_days_to_response"] == 4.0

    sources = {b["key"]: (b["applied"], b["responded"]) for b in body["by_source"]}
    assert sources == {"LinkedIn": (2, 1), "Referral": (2, 2)}
    roles = {b["key"]: b["rate"] for b in body["by_role_type"]}
    assert roles == {"intern": 0.5, "full_time": 1.0}
    weekdays = {b["key"]: (b["applied"], b["responded"]) for b in body["by_weekday"]}
    assert weekdays["Mon"] == (2, 1) and weekdays["Wed"] == (2, 2) and weekdays["Fri"] == (0, 0)


def test_pulse_with_nothing(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    body = client.get("/api/analytics/pulse").json()
    assert body["applied"] == 0 and body["response_rate"] is None
    assert body["median_days_to_response"] is None
