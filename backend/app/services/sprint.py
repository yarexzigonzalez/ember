from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.user import User
from app.services.calendar import user_today, week_bounds
from app.services.metrics import streak, weekly_counts

# Streaks longer than two years are a flex we can afford to not compute.
LOOKBACK_WEEKS = 104
HISTORY_WEEKS = 8


@dataclass
class Sprint:
    goal: int
    week_start: date
    week_end: date
    count: int
    streak: int
    history: list[tuple[date, int]]


def weekly_sprint(db: Session, user: User, now: datetime | None = None) -> Sprint:
    today = user_today(user.timezone, now)
    monday, sunday = week_bounds(today)
    since = monday - timedelta(weeks=LOOKBACK_WEEKS)
    dates = db.scalars(
        select(Application.applied_at).where(
            Application.user_id == user.id,
            Application.applied_at.is_not(None),
            Application.applied_at >= since,
            Application.applied_at <= sunday,
        )
    ).all()
    counts = weekly_counts(d for d in dates if d is not None)
    history = [
        (monday - timedelta(weeks=back), counts.get(monday - timedelta(weeks=back), 0))
        for back in range(HISTORY_WEEKS - 1, -1, -1)
    ]
    return Sprint(
        goal=user.weekly_goal,
        week_start=monday,
        week_end=sunday,
        count=counts.get(monday, 0),
        streak=streak(counts, monday, user.weekly_goal),
        history=history,
    )
