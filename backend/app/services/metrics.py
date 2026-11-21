"""Every metric definition lives here. Dashboard, analytics (naive *and*
optimized), sprint, exports — they all import from this file so nobody
quietly invents their own version of "response rate".

The rules:
- A *response* is the first time an application moves into oa, interview,
  offer, or rejected. Rejection counts, because hearing "no" is still hearing
  back. ghosted and saved don't count.
- Response rate = applications with a response / applications with applied_at.
  Saved jobs (no applied_at) are out of both the top and the bottom.
- Time to first response = date of that first response (in the user's tz)
  minus applied_at, in days. Skipped when applied_at is empty.
- Weekly sprint = applications whose applied_at lands in the current
  Monday-Sunday week in the user's timezone. Every role_type counts.
- Streak = consecutive weeks hitting weekly_goal, counting back from this
  week if it's already hit, otherwise from last week (so an in-progress
  week doesn't zero you out on Monday morning).
"""

from collections.abc import Iterable
from datetime import date, timedelta

from app.services.calendar import week_start

RESPONSE_STATUSES = frozenset({"oa", "interview", "offer", "rejected"})


def is_response(to_status: str) -> bool:
    return to_status in RESPONSE_STATUSES


def response_rate(responded: int, applied: int) -> float | None:
    if applied == 0:
        return None
    return responded / applied


def days_to_response(applied_at: date, responded_on: date) -> int:
    # Clamp at 0: if someone backdates applied_at past an event, don't go negative.
    return max(0, (responded_on - applied_at).days)


def weekly_counts(applied_dates: Iterable[date]) -> dict[date, int]:
    """Monday -> how many applications that week."""
    counts: dict[date, int] = {}
    for day in applied_dates:
        monday = week_start(day)
        counts[monday] = counts.get(monday, 0) + 1
    return counts


def streak(counts: dict[date, int], this_monday: date, goal: int) -> int:
    cursor = this_monday if counts.get(this_monday, 0) >= goal else this_monday - timedelta(7)
    total = 0
    while counts.get(cursor, 0) >= goal:
        total += 1
        cursor -= timedelta(days=7)
    return total
