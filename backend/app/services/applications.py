from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.status_event import StatusEvent
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.dedupe import make_dedupe_key


class DuplicateApplicationError(Exception):
    pass


def _touch_applied_at(application: Application, when: datetime) -> None:
    if application.status == ApplicationStatus.APPLIED and application.applied_at is None:
        application.applied_at = when.date()


def _add_event(
    db: Session,
    application: Application,
    from_status: str | None,
    to_status: str,
    when: datetime,
) -> None:
    db.add(
        StatusEvent(
            application_id=application.id,
            user_id=application.user_id,
            from_status=from_status,
            to_status=to_status,
            occurred_at=when,
        )
    )
    application.last_status_at = when


def get_owned(db: Session, user: User, application_id) -> Application | None:
    return db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user.id,
        )
    )


def create_application(db: Session, user: User, body: ApplicationCreate) -> Application:
    key = make_dedupe_key(body.company, body.role, body.posting_url)
    clash = db.scalar(
        select(Application.id).where(
            Application.user_id == user.id,
            Application.dedupe_key == key,
        )
    )
    if clash is not None:
        raise DuplicateApplicationError

    now = datetime.now(UTC)
    application = Application(
        user_id=user.id,
        company=body.company.strip(),
        role=body.role.strip(),
        location=_clean(body.location),
        source=_clean(body.source),
        posting_url=_clean(body.posting_url),
        dedupe_key=key,
        status=body.status.value,
        seniority=_clean(body.seniority),
        role_type=_clean(body.role_type),
        requirements=body.requirements,
        notes=_clean(body.notes),
        applied_at=body.applied_at,
        last_status_at=now,
    )
    _touch_applied_at(application, now)
    db.add(application)
    db.flush()
    _add_event(db, application, None, application.status, now)
    db.commit()
    db.refresh(application)
    return application


def update_application(
    db: Session, user: User, application: Application, body: ApplicationUpdate
) -> Application:
    data = body.model_dump(exclude_unset=True)
    company = data.get("company", application.company)
    role = data.get("role", application.role)
    posting_url = data.get("posting_url", application.posting_url)
    key = make_dedupe_key(company, role, posting_url)
    if key != application.dedupe_key:
        clash = db.scalar(
            select(Application.id).where(
                Application.user_id == user.id,
                Application.dedupe_key == key,
                Application.id != application.id,
            )
        )
        if clash is not None:
            raise DuplicateApplicationError
        application.dedupe_key = key

    now = datetime.now(UTC)
    previous = application.status
    for field in (
        "company",
        "role",
        "location",
        "source",
        "posting_url",
        "seniority",
        "role_type",
        "notes",
    ):
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None if field not in {"company", "role"} else value.strip()
            setattr(application, field, value)
    if "requirements" in data:
        application.requirements = data["requirements"]
    if "applied_at" in data:
        application.applied_at = data["applied_at"]
    if "status" in data:
        application.status = data["status"].value
        if application.status != previous:
            _add_event(db, application, previous, application.status, now)
    _touch_applied_at(application, now)
    db.commit()
    db.refresh(application)
    return application


def delete_application(db: Session, application: Application) -> None:
    db.delete(application)
    db.commit()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
