"""The whole point of keeping naive around: both versions have to agree."""

import uuid
from datetime import date

import pytest
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models.application import Application
from app.models.user import User
from app.schemas.application import ApplicationListParams
from app.services.analytics.naive import market_pulse_naive
from app.services.analytics.optimized import market_pulse_optimized
from app.services.fake_data import insert_fake
from app.services.importing.naive import import_naive
from app.services.importing.optimized import import_optimized
from app.services.importing.parse import parse_csv
from app.services.listing.naive import list_applications_naive
from app.services.listing.optimized import list_applications_optimized


def _make_user(db, tz: str = "America/Los_Angeles") -> User:
    user = User(email=f"bench-{uuid.uuid4().hex}@ember.dev", password_hash="x", timezone=tz)
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def db():
    session = SessionLocal()
    made: list[uuid.UUID] = []
    session.info["made"] = made
    yield session
    session.rollback()
    session.execute(delete(User).where(User.id.in_(made)))
    session.commit()
    session.close()


@pytest.fixture
def seeded(db):
    user = _make_user(db)
    db.info["made"].append(user.id)
    insert_fake(db, user.id, 600, seed=11, today=date(2026, 11, 20))
    return user


def test_pulse_matches(db, seeded) -> None:
    for tz in ("America/Los_Angeles", "Asia/Tokyo", "UTC"):
        naive = market_pulse_naive(db, seeded.id, tz)
        fast = market_pulse_optimized(db, seeded.id, tz)
        assert naive == fast, tz
    assert naive.applied > 300 and naive.responded > 30


SORTS = ["updated_at", "company", "role", "status", "applied_at"]


@pytest.mark.parametrize("sort", SORTS)
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_list_matches(db, seeded, sort, direction) -> None:
    combos = [
        {},
        {"q": "stripe"},
        {"q": "intern", "status": "applied"},
        {"source": "Referral"},
        {"q": "REMOTE", "page": 2, "page_size": 7},
        {"q": "nothing-matches-this"},
    ]
    for extra in combos:
        params = ApplicationListParams(sort=sort, direction=direction, **extra)
        naive_rows, naive_total = list_applications_naive(db, seeded.id, params)
        fast_rows, fast_total = list_applications_optimized(db, seeded.id, params)
        assert naive_total == fast_total, extra
        key = {
            "company": lambda r: r.company.lower(),
            "role": lambda r: r.role.lower(),
            "status": lambda r: r.status,
            "applied_at": lambda r: r.applied_at,
            "updated_at": lambda r: r.updated_at,
        }[sort]
        # Ties can land in any order in naive, so compare the sort values page by page.
        assert [key(r) for r in naive_rows] == [key(r) for r in fast_rows], extra


def test_import_matches(db) -> None:
    csv_text = (
        "company,role,link,date,status\n"
        + "".join(
            f"Co{i % 40},Role{i % 7},https://x.com/{i % 55},2026-10-{(i % 28) + 1:02d},\n"
            for i in range(300)
        )
        + "Broken,,,,\nBad,Date,,10/1/2026,\nBad,Status,,,nope\n"
    )
    results = []
    keys = []
    for runner in (import_naive, import_optimized):
        user = _make_user(db)
        db.info["made"].append(user.id)
        # import twice: second pass should be all skips
        first = runner(db, user, parse_csv(csv_text))
        second = runner(db, user, parse_csv(csv_text))
        results.append(
            (first.added, first.skipped, len(first.errors), second.added, second.skipped)
        )
        keys.append(
            sorted(db.scalars(select(Application.dedupe_key).where(Application.user_id == user.id)))
        )
    assert results[0] == results[1]
    assert keys[0] == keys[1]
    assert results[0][3] == 0  # nothing new the second time
