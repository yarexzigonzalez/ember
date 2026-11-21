from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.auth.tokens import hash_session_token
from app.config import settings
from app.db import get_db
from app.models.session import Session as AuthSession
from app.models.user import User


def get_current_user(
    request: Request,
    db: DbSession = Depends(get_db),
) -> User:
    raw_token = request.cookies.get(settings.cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token_hash = hash_session_token(raw_token)
    auth_session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).one_or_none()
    if auth_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if auth_session.expires_at < datetime.now(UTC):
        db.delete(auth_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = db.get(User, auth_session.user_id)
    if user is None:
        db.delete(auth_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
