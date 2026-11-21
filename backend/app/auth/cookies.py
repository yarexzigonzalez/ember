from typing import Literal

from fastapi import Response

from app.config import settings

SameSite = Literal["lax", "strict", "none"]


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )
