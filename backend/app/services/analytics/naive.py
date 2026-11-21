"""Naive Market Pulse: pull every row into Python and loop.

This is the "before" in the benchmark. Two full table loads per request
(applications + all their status events), then dicts and a sort for the
median. Totally fine at 50 rows. At 50k it's a lot of objects for no reason.
Kept on purpose, don't delete it.
"""

import uuid
from datetime import date
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.status_event import StatusEvent
from app.services.analytics.report import PulseReport, finish_buckets, weekday_buckets
from app.services.calendar import local_date
from app.services.metrics import days_to_response, is_response


def market_pulse_naive(db: Session, user_id: uuid.UUID, tz: str) -> PulseReport:
    applications = db.scalars(select(Application).where(Application.user_id == user_id)).all()
    events = db.scalars(select(StatusEvent).where(StatusEvent.user_id == user_id)).all()

    # first response per application
    first_response: dict[uuid.UUID, date] = {}
    for event in sorted(events, key=lambda e: e.occurred_at):
        if is_response(event.to_status) and event.application_id not in first_response:
            first_response[event.application_id] = local_date(event.occurred_at, tz)

    by_source: dict[str, list[int]] = {}
    by_role: dict[str, list[int]] = {}
    by_weekday: dict[int, list[int]] = {}
    waits: list[int] = []
    applied = responded = 0

    for app in applications:
        if app.applied_at is None:
            continue  # saved jobs stay out of the denominator
        got = app.id in first_response
        applied += 1
        responded += got
        for bucket, key in (
            (by_source, app.source or "Unknown"),
            (by_role, app.role_type or "unknown"),
        ):
            row = bucket.setdefault(key, [0, 0])
            row[0] += 1
            row[1] += got
        day = by_weekday.setdefault(app.applied_at.weekday(), [0, 0])
        day[0] += 1
        day[1] += got
        if got:
            waits.append(days_to_response(app.applied_at, first_response[app.id]))

    return PulseReport(
        applied=applied,
        responded=responded,
        median_days_to_response=float(median(waits)) if waits else None,
        by_source=finish_buckets(by_source),
        by_role_type=finish_buckets(by_role),
        by_weekday=weekday_buckets(by_weekday),
    )
