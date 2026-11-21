from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationListParams


def list_applications_naive(
    db: Session, user_id, params: ApplicationListParams
) -> tuple[list[Application], int]:
    """Load this user's rows, then filter and sort in Python.

    Fine for a handful of apps. Falls over once the table gets big,
    which is the point of keeping it.
    """
    rows = list(
        db.scalars(select(Application).where(Application.user_id == user_id)).all()
    )
    if params.status:
        rows = [row for row in rows if row.status == params.status]
    if params.source:
        rows = [row for row in rows if (row.source or "") == params.source]
    if params.q:
        needle = params.q.lower()
        rows = [
            row
            for row in rows
            if needle in row.company.lower()
            or needle in row.role.lower()
            or needle in (row.location or "").lower()
        ]

    rows.sort(key=lambda row: _sort_value(row, params.sort), reverse=params.direction == "desc")
    total = len(rows)
    start = (params.page - 1) * params.page_size
    return rows[start : start + params.page_size], total


def _sort_value(row: Application, sort: str) -> str | datetime | date:
    if sort == "company":
        return row.company.lower()
    if sort == "role":
        return row.role.lower()
    if sort == "status":
        return row.status
    if sort == "applied_at":
        return row.applied_at or date.min
    return row.updated_at
