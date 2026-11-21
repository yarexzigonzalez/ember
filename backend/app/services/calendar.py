"""Dates in the user's own timezone.

Everything week-shaped (sprint goal, streaks, "applied on a Tuesday") runs
off the user's local calendar, not UTC. Otherwise someone in LA who applies
Sunday at 9pm gets counted in next week.

Weeks start Monday. applied_at is a plain DATE, already local, so once we
know "today" for the user the rest is just date math.
"""

from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones


@lru_cache(maxsize=1)
def _known_zones() -> frozenset[str]:
    return frozenset(available_timezones())


def is_valid_timezone(name: str) -> bool:
    return name in _known_zones()


def local_now(tz: str, now: datetime | None = None) -> datetime:
    moment = now or datetime.now(UTC)
    return moment.astimezone(ZoneInfo(tz))


def user_today(tz: str, now: datetime | None = None) -> date:
    return local_now(tz, now).date()


def local_date(moment: datetime, tz: str) -> date:
    return moment.astimezone(ZoneInfo(tz)).date()


def week_start(day: date) -> date:
    """Monday of the week this day lands in."""
    return day - timedelta(days=day.weekday())


def week_bounds(day: date) -> tuple[date, date]:
    """(monday, sunday), both inclusive."""
    monday = week_start(day)
    return monday, monday + timedelta(days=6)
