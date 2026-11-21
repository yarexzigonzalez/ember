from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.auth.cookies import clear_session_cookie, set_session_cookie
from app.auth.passwords import hash_password, verify_dummy_password, verify_password
from app.auth.tokens import hash_session_token, new_session_token
from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.middleware.rate_limit import limit_auth_endpoints
from app.models.session import Session as AuthSession
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, SettingsUpdate, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_session(db: DbSession, user: User) -> str:
    raw_token = new_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds),
        )
    )
    db.commit()
    return raw_token


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_auth_endpoints)],
)
def register(body: RegisterRequest, db: DbSession = Depends(get_db)) -> User:
    user = User(
        email=str(body.email),
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        timezone=body.timezone or "UTC",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=UserPublic, dependencies=[Depends(limit_auth_endpoints)])
def login(
    body: LoginRequest,
    response: Response,
    db: DbSession = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.email == str(body.email)).one_or_none()
    if user is None:
        verify_dummy_password(body.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    set_session_cookie(response, _issue_session(db, user))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)) -> None:
    raw_token = request.cookies.get(settings.cookie_name)
    if raw_token:
        token_hash = hash_session_token(raw_token)
        auth_session = (
            db.query(AuthSession).filter(AuthSession.token_hash == token_hash).one_or_none()
        )
        if auth_session is not None:
            db.delete(auth_session)
            db.commit()
    clear_session_cookie(response)


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_settings(
    body: SettingsUpdate,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.is_demo:
        # Shared account. Nobody gets to move its timezone or goal on everyone else.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The demo account's settings are locked",
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is None and field != "display_name":
            continue
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
