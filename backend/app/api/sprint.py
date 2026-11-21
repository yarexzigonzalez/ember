from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.sprint import weekly_sprint

router = APIRouter(prefix="/sprint", tags=["sprint"])


class WeekCount(BaseModel):
    week_start: date
    count: int


class SprintOut(BaseModel):
    goal: int
    week_start: date
    week_end: date
    count: int
    streak: int
    history: list[WeekCount]


@router.get("", response_model=SprintOut)
def sprint(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SprintOut:
    result = weekly_sprint(db, user)
    return SprintOut(
        goal=result.goal,
        week_start=result.week_start,
        week_end=result.week_end,
        count=result.count,
        streak=result.streak,
        history=[WeekCount(week_start=w, count=c) for w, c in result.history],
    )
