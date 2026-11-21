import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.enums import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationList,
    ApplicationListParams,
    ApplicationPublic,
    ApplicationUpdate,
    SortDirection,
    SortField,
)
from app.services.applications import (
    DuplicateApplicationError,
    create_application,
    delete_application,
    get_owned,
    update_application,
)
from app.services.demo import demo_is_full
from app.services.listing.optimized import list_applications_optimized

router = APIRouter(prefix="/applications", tags=["applications"])


def _list_params(
    q: str | None = Query(default=None, max_length=200),
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    source: str | None = Query(default=None, max_length=80),
    sort: SortField = Query(default="updated_at"),
    direction: SortDirection = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> ApplicationListParams:
    return ApplicationListParams(
        q=q,
        status=status_filter,
        source=source,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )


@router.get("", response_model=ApplicationList)
def list_applications(
    params: ApplicationListParams = Depends(_list_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationList:
    items, total = list_applications_optimized(db, user.id, params)
    return ApplicationList(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=ApplicationPublic, status_code=status.HTTP_201_CREATED)
def create(
    body: ApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationPublic:
    if user.is_demo and demo_is_full(db, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo board is full. It resets tonight, or make your own account.",
        )
    try:
        return create_application(db, user, body)
    except DuplicateApplicationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have this company, role, and link",
        ) from None


@router.get("/{application_id}", response_model=ApplicationPublic)
def read_one(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationPublic:
    application = get_owned(db, user, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return application


@router.patch("/{application_id}", response_model=ApplicationPublic)
def patch(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationPublic:
    application = get_owned(db, user, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        return update_application(db, user, application, body)
    except DuplicateApplicationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have this company, role, and link",
        ) from None


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    application = get_owned(db, user, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    delete_application(db, application)
