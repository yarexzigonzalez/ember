from datetime import UTC, date, datetime

from app.services.calendar import is_valid_timezone, user_today, week_bounds

LA = "America/Los_Angeles"


def _utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


def test_sunday_night_vs_monday_morning_in_la() -> None:
    # Sun Nov 15 2026, 23:59 in LA (PST, UTC-8) = Mon Nov 16 07:59 UTC.
    sunday_night = user_today(LA, _utc(2026, 11, 16, 7, 59))
    monday_morning = user_today(LA, _utc(2026, 11, 16, 8, 1))
    assert sunday_night == date(2026, 11, 15)
    assert monday_morning == date(2026, 11, 16)
    assert week_bounds(sunday_night) == (date(2026, 11, 9), date(2026, 11, 15))
    assert week_bounds(monday_morning) == (date(2026, 11, 16), date(2026, 11, 22))


def test_dst_fallback_week_keeps_its_shape() -> None:
    # DST ended Sun Nov 1 2026 at 2am in LA. That Sunday was 25 hours long.
    # 07:30 UTC on Nov 2 is still Sunday night locally (UTC-8 by then).
    last_minute = user_today(LA, _utc(2026, 11, 2, 7, 30))
    assert last_minute == date(2026, 11, 1)
    assert week_bounds(last_minute) == (date(2026, 10, 26), date(2026, 11, 1))
    # Hour later it's Monday, new week.
    assert week_bounds(user_today(LA, _utc(2026, 11, 2, 8, 30)))[0] == date(2026, 11, 2)


def test_dst_spring_forward_week() -> None:
    # Clocks jumped Sun Mar 8 2026. Monday 00:30 PDT = 07:30 UTC.
    assert user_today(LA, _utc(2026, 3, 9, 7, 30)) == date(2026, 3, 9)
    assert user_today(LA, _utc(2026, 3, 9, 6, 30)) == date(2026, 3, 8)


def test_timezone_ahead_of_utc() -> None:
    # Sunday afternoon in UTC is already Monday in Tokyo.
    tokyo_day = user_today("Asia/Tokyo", _utc(2026, 11, 15, 16, 0))
    assert tokyo_day == date(2026, 11, 16)
    assert week_bounds(tokyo_day)[0] == date(2026, 11, 16)
    # Same instant in UTC is still last week.
    assert week_bounds(user_today("UTC", _utc(2026, 11, 15, 16, 0)))[0] == date(2026, 11, 9)


def test_timezone_validation() -> None:
    assert is_valid_timezone("America/Chicago")
    assert not is_valid_timezone("PST-8")
    assert not is_valid_timezone("Mars/Olympus_Mons")
