from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.analytics.naive import market_pulse_naive
from app.services.analytics.report import Bucket, PulseReport

router = APIRouter(prefix="/analytics", tags=["analytics"])


class BucketOut(BaseModel):
    key: str
    applied: int
    responded: int
    rate: float | None


class PulseOut(BaseModel):
    applied: int
    responded: int
    response_rate: float | None
    median_days_to_response: float | None
    by_source: list[BucketOut]
    by_role_type: list[BucketOut]
    by_weekday: list[BucketOut]


def _buckets(items: list[Bucket]) -> list[BucketOut]:
    return [
        BucketOut(key=b.key, applied=b.applied, responded=b.responded, rate=b.rate)
        for b in items
    ]


def to_out(report: PulseReport) -> PulseOut:
    return PulseOut(
        applied=report.applied,
        responded=report.responded,
        response_rate=report.responded / report.applied if report.applied else None,
        median_days_to_response=report.median_days_to_response,
        by_source=_buckets(report.by_source),
        by_role_type=_buckets(report.by_role_type),
        by_weekday=_buckets(report.by_weekday),
    )


@router.get("/pulse", response_model=PulseOut)
def pulse(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> PulseOut:
    return to_out(market_pulse_naive(db, user.id, user.timezone))
