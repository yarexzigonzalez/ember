"""Optimized import: one query for what you already have, a couple of big
INSERTs, one commit.

- existing dedupe keys -> a Python set (one SELECT instead of one per row)
- duplicates inside the same file get caught by that same set
- applications go in with multi-row INSERT ... ON CONFLICT DO NOTHING
  RETURNING, so a race with another request can't double-insert
- status events go in as one more bulk INSERT
"""

from datetime import UTC, datetime

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.status_event import StatusEvent
from app.models.user import User
from app.services.calendar import local_date
from app.services.dedupe import make_dedupe_key
from app.services.importing.naive import ImportResult
from app.services.importing.parse import Parsed

CHUNK = 1_000


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def import_optimized(db: Session, user: User, parsed: Parsed) -> ImportResult:
    result = ImportResult(errors=list(parsed.errors))
    seen = set(db.scalars(select(Application.dedupe_key).where(Application.user_id == user.id)))
    now = datetime.now(UTC)
    today = local_date(now, user.timezone)

    pending: list[dict] = []
    for _number, row in parsed.rows:
        key = make_dedupe_key(row.company, row.role, row.posting_url)
        if key in seen:
            result.skipped += 1
            continue
        seen.add(key)
        applied_at = row.applied_at
        if row.status == ApplicationStatus.APPLIED and applied_at is None:
            applied_at = today
        pending.append(
            {
                "user_id": user.id,
                "company": row.company.strip(),
                "role": row.role.strip(),
                "location": _clean(row.location),
                "source": _clean(row.source),
                "posting_url": _clean(row.posting_url),
                "dedupe_key": key,
                "status": row.status.value,
                "seniority": _clean(row.seniority),
                "role_type": _clean(row.role_type),
                "requirements": row.requirements,
                "notes": _clean(row.notes),
                "applied_at": applied_at,
                "last_status_at": now,
            }
        )

    for start in range(0, len(pending), CHUNK):
        chunk = pending[start : start + CHUNK]
        inserted = db.execute(
            pg_insert(Application)
            .values(chunk)
            .on_conflict_do_nothing(constraint="uq_applications_user_id_dedupe_key")
            .returning(Application.id, Application.status)
        ).all()
        result.added += len(inserted)
        result.skipped += len(chunk) - len(inserted)
        if inserted:
            db.execute(
                insert(StatusEvent),
                [
                    {
                        "application_id": app_id,
                        "user_id": user.id,
                        "from_status": None,
                        "to_status": status,
                        "occurred_at": now,
                    }
                    for app_id, status in inserted
                ],
            )
    db.commit()
    return result
