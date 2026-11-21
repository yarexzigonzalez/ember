from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.middleware.rate_limit import rate_limit
from app.models.user import User
from app.services.extract.protocol import ExtractedJob, JobExtractor
from app.services.extract.service import Via, default_llm, extract_job

router = APIRouter(prefix="/extract", tags=["extract"])

MAX_PASTE = 20_000


class ExtractRequest(BaseModel):
    text: str = Field(min_length=20, max_length=MAX_PASTE)


class ExtractResponse(BaseModel):
    job: ExtractedJob
    via: Via


def get_llm() -> JobExtractor | None:
    """Own dependency so tests can override it with a fake."""
    return default_llm()


def _limit(request: Request) -> None:
    rate_limit("extract", settings.extract_rate_limit, settings.extract_rate_window_seconds)(
        request
    )


@router.post("", response_model=ExtractResponse, dependencies=[Depends(_limit)])
def extract(
    body: ExtractRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    llm: JobExtractor | None = Depends(get_llm),
) -> ExtractResponse:
    # Demo is public, so strangers don't get to run up the API bill. Regex only.
    job, via = extract_job(db, body.text, llm, allow_llm=not user.is_demo)
    return ExtractResponse(job=job, via=via)
