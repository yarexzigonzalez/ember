"""Optimized list: Postgres filters, sorts, and pages. We only ever pull back
one page of rows, plus a count from the same query via a window function.

Ordering matches naive.py exactly (case-insensitive names, empty applied_at
first when ascending / last when descending) and adds id as a tiebreaker so
pages never shuffle between requests.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationListParams


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_applications_optimized(
    db: Session, user_id: uuid.UUID, params: ApplicationListParams
) -> tuple[list[Application], int]:
    query = select(Application, func.count().over().label("total")).where(
        Application.user_id == user_id
    )
    if params.status:
        query = query.where(Application.status == params.status)
    if params.source:
        query = query.where(Application.source == params.source)
    if params.q:
        needle = f"%{_escape_like(params.q)}%"
        query = query.where(
            or_(
                Application.company.ilike(needle, escape="\\"),
                Application.role.ilike(needle, escape="\\"),
                Application.location.ilike(needle, escape="\\"),
            )
        )

    desc = params.direction == "desc"
    column = {
        "company": func.lower(Application.company),
        "role": func.lower(Application.role),
        "status": Application.status,
        "applied_at": Application.applied_at,
        "updated_at": Application.updated_at,
    }[params.sort]
    order = column.desc() if desc else column.asc()
    if params.sort == "applied_at":
        order = order.nulls_last() if desc else order.nulls_first()
    tiebreak = Application.id.desc() if desc else Application.id.asc()

    rows = db.execute(
        query.order_by(order, tiebreak)
        .limit(params.page_size)
        .offset((params.page - 1) * params.page_size)
    ).all()
    if rows:
        return [row[0] for row in rows], rows[0].total
    if params.page == 1:
        return [], 0
    # Asked for a page past the end: still report the real total.
    count_query = query.with_only_columns(func.count()).order_by(None)
    return [], db.scalar(count_query) or 0
