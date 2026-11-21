import csv
import io
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.user import User

COLUMNS = ["company", "role", "link", "date", "status", "source", "location", "notes"]


def _safe(value: object) -> str:
    """Stop spreadsheet formula injection: a cell starting with = + - @ gets a ' in front."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def export_rows(db: Session, user: User, limit: int | None = None) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def flush() -> str:
        chunk = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return chunk

    writer.writerow(COLUMNS)
    yield flush()
    query = (
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.created_at)
        .limit(limit)
    )
    for app in db.scalars(query).yield_per(500):
        writer.writerow(
            [
                _safe(app.company),
                _safe(app.role),
                _safe(app.posting_url),
                app.applied_at.isoformat() if app.applied_at else "",
                app.status,
                _safe(app.source),
                _safe(app.location),
                _safe(app.notes),
            ]
        )
        yield flush()
