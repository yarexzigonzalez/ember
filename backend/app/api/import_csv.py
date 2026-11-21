from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.middleware.rate_limit import rate_limit
from app.models.user import User
from app.services.exporting import export_rows
from app.services.importing.optimized import import_optimized
from app.services.importing.parse import MAX_BYTES, CsvTooBig, parse_csv

router = APIRouter(tags=["import"])

# Shared account: let visitors try it, but not dump 5k rows on everyone.
DEMO_MAX_ROWS = 25
DEMO_MAX_EXPORT = 200


class ImportRequest(BaseModel):
    # Frontend reads the file in the browser and sends text. One path for paste + upload.
    csv: str = Field(min_length=1, max_length=MAX_BYTES)


class RowErrorOut(BaseModel):
    row: int
    message: str


class ImportOut(BaseModel):
    added: int
    skipped: int
    errors: list[RowErrorOut]


def _limit(request: Request) -> None:
    rate_limit("import", 30, 60 * 60)(request)


@router.post("/import", response_model=ImportOut, dependencies=[Depends(_limit)])
def import_csv(
    body: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportOut:
    try:
        parsed = parse_csv(body.csv, max_rows=DEMO_MAX_ROWS if user.is_demo else 5_000)
    except (CsvTooBig, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from None
    result = import_optimized(db, user, parsed)
    return ImportOut(
        added=result.added,
        skipped=result.skipped,
        errors=[RowErrorOut(row=e.row, message=e.message) for e in result.errors],
    )


@router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> StreamingResponse:
    return StreamingResponse(
        export_rows(db, user, limit=DEMO_MAX_EXPORT if user.is_demo else None),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ember-applications.csv"'},
    )
