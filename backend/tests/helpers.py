"""Shared bits for tests that need to fake time on rows."""

from datetime import datetime

from sqlalchemy import text

from app.db import SessionLocal


def backdate(application_id: str, last_status_at: datetime) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE applications SET last_status_at = :when WHERE id = :id"),
            {"when": last_status_at, "id": application_id},
        )
        db.commit()
    finally:
        db.close()
