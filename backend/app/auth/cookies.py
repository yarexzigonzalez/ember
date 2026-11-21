from fastapi import Response

from app.config import settings

# Same-origin setup (Vercel proxies /api), so Lax is all we need. No Domain
# attribute on purpose: the cookie sticks to whatever host served it.


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
