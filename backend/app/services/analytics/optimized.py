"""Optimized Market Pulse: one SQL round trip, Postgres does the counting.

The first-response CTE walks status_events for this user only (index on
user_id, occurred_at), GROUPING SETS gives us by-source, by-role-type,
by-weekday, and the overall totals in one pass, and percentile_cont handles
the median. Python just reshapes ~20 rows instead of 50k objects.

Same definitions as naive.py (both pull from services/metrics.py), and a
test makes sure they agree.
"""

import uuid

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services.analytics.report import PulseReport, finish_buckets, weekday_buckets
from app.services.metrics import RESPONSE_STATUSES

_QUERY = text(
    """
    WITH first_response AS (
        SELECT application_id, min(occurred_at) AS first_at
        FROM status_events
        WHERE user_id = :user_id AND to_status IN :responses
        GROUP BY application_id
    ),
    applied AS (
        SELECT
            coalesce(a.source, 'Unknown') AS source,
            coalesce(a.role_type, 'unknown') AS role_type,
            extract(isodow FROM a.applied_at)::int - 1 AS weekday,
            f.first_at IS NOT NULL AS responded,
            CASE WHEN f.first_at IS NOT NULL THEN
                greatest(0, (f.first_at AT TIME ZONE :tz)::date - a.applied_at)
            END AS wait_days
        FROM applications a
        LEFT JOIN first_response f ON f.application_id = a.id
        WHERE a.user_id = :user_id AND a.applied_at IS NOT NULL
    )
    SELECT
        grouping(source, role_type, weekday) AS level,
        source, role_type, weekday,
        count(*) AS applied,
        count(*) FILTER (WHERE responded) AS responded,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY wait_days) AS median_wait
    FROM applied
    GROUP BY GROUPING SETS ((source), (role_type), (weekday), ())
    """
).bindparams(bindparam("responses", expanding=True))

# grouping() bitmask: 1 bit per column in (source, role_type, weekday), set = rolled up
_BY_SOURCE, _BY_ROLE, _BY_WEEKDAY, _TOTAL = 0b011, 0b101, 0b110, 0b111


def market_pulse_optimized(db: Session, user_id: uuid.UUID, tz: str) -> PulseReport:
    rows = db.execute(
        _QUERY, {"user_id": user_id, "tz": tz, "responses": sorted(RESPONSE_STATUSES)}
    ).all()
    by_source: dict[str, list[int]] = {}
    by_role: dict[str, list[int]] = {}
    by_weekday: dict[int, list[int]] = {}
    applied = responded = 0
    median: float | None = None
    for row in rows:
        counts = [row.applied, row.responded]
        if row.level == _BY_SOURCE:
            by_source[row.source] = counts
        elif row.level == _BY_ROLE:
            by_role[row.role_type] = counts
        elif row.level == _BY_WEEKDAY:
            by_weekday[row.weekday] = counts
        elif row.level == _TOTAL:
            applied, responded = row.applied, row.responded
            median = float(row.median_wait) if row.median_wait is not None else None
    return PulseReport(
        applied=applied,
        responded=responded,
        median_days_to_response=median,
        by_source=finish_buckets(by_source),
        by_role_type=finish_buckets(by_role),
        by_weekday=weekday_buckets(by_weekday),
    )
