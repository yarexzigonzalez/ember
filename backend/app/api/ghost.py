import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.middleware.rate_limit import rate_limit
from app.models.user import User
from app.schemas.application import ApplicationPublic
from app.services.applications import get_owned
from app.services.ghost import OPEN_STATUSES, ghost_candidates, llm_draft, template_draft

router = APIRouter(prefix="/ghost", tags=["ghost"])


class GhostItem(BaseModel):
    application: ApplicationPublic
    days_quiet: int


class GhostList(BaseModel):
    after_days: int
    items: list[GhostItem]


class Draft(BaseModel):
    text: str
    via: Literal["llm", "template"]


@router.get("", response_model=GhostList)
def list_ghosts(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> GhostList:
    items = [
        GhostItem(application=c.application, days_quiet=c.days_quiet)  # type: ignore[arg-type]
        for c in ghost_candidates(db, user)
    ]
    return GhostList(after_days=user.ghost_after_days, items=items)


def _limit(request: Request) -> None:
    rate_limit("draft", settings.extract_rate_limit, settings.extract_rate_window_seconds)(
        request
    )


@router.post("/{application_id}/draft", response_model=Draft, dependencies=[Depends(_limit)])
def draft(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Draft:
    application = get_owned(db, user, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if application.status not in OPEN_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That one's closed out")
    days = (datetime.now(UTC) - application.last_status_at).days
    text = None if user.is_demo else llm_draft(application, days, user.display_name)
    if text:
        return Draft(text=text, via="llm")
    return Draft(text=template_draft(application, days, user.display_name), via="template")
