from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.services.calendar import user_today, week_start
from app.services.metrics import streak, weekly_counts

MON = date(2026, 11, 16)


def test_streak_counts_back_from_last_week_while_this_one_is_in_progress() -> None:
    counts = {MON - timedelta(7): 12, MON - timedelta(14): 15, MON: 3}
    assert streak(counts, MON, goal=12) == 2


def test_streak_includes_this_week_once_hit() -> None:
    counts = {MON: 12, MON - timedelta(7): 12}
    assert streak(counts, MON, goal=12) == 2


def test_missed_week_resets_streak() -> None:
    counts = {MON - timedelta(7): 12, MON - timedelta(14): 4, MON - timedelta(21): 20}
    assert streak(counts, MON, goal=12) == 1
    assert streak({MON - timedelta(14): 30}, MON, goal=12) == 0


def test_weekly_counts_bucket_by_monday() -> None:
    sunday, monday = date(2026, 11, 15), date(2026, 11, 16)
    assert weekly_counts([sunday, monday, monday]) == {date(2026, 11, 9): 1, monday: 2}


def test_sprint_endpoint_counts_every_role_type(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    client.patch("/api/auth/me", json={"weekly_goal": 2})
    today = user_today("UTC")
    this_monday = week_start(today)
    last_week = this_monday - timedelta(days=3)
    rows = [
        ("A", "intern", today),
        ("B", "full_time", this_monday),
        ("C", "contract", last_week),
        ("D", None, last_week),
        ("E", "intern", None),  # saved, never applied: doesn't count
    ]
    for company, role_type, applied in rows:
        payload = {"company": company, "role": "Eng", "role_type": role_type}
        if applied:
            payload |= {"status": "applied", "applied_at": applied.isoformat()}
        assert client.post("/api/applications", json=payload).status_code == 201

    body = client.get("/api/sprint").json()
    assert body["goal"] == 2
    assert body["count"] == 2
    assert body["week_start"] == this_monday.isoformat()
    assert body["streak"] == 2  # last week 2, this week 2
    assert body["history"][-1] == {"week_start": this_monday.isoformat(), "count": 2}
    assert len(body["history"]) == 8
