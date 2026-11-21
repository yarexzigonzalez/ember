"""The shared demo account.

One user, fixed timezone, no usable password (you only get in through the
demo button). Visitors can drag cards around and add stuff, it all gets wiped
and reseeded nightly by scripts/reset_demo.py.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.models.application import Application
from app.models.session import Session as AuthSession
from app.models.user import User
from app.services.calendar import user_today
from app.services.fake_data import insert_fake

DEMO_EMAIL = "demo@ember.app"
DEMO_TIMEZONE = "America/Los_Angeles"
DEMO_SESSION_SECONDS = 4 * 60 * 60
# Enough rows for the charts to look real. Visitors can't push it past the cap.
DEMO_ROWS = 160
DEMO_MAX_ROWS = 400


def get_demo_user(db: Session) -> User | None:
    return db.scalar(select(User).where(User.email == DEMO_EMAIL, User.is_demo.is_(True)))


def demo_is_full(db: Session, user: User) -> bool:
    count = db.scalar(select(func.count()).where(Application.user_id == user.id)) or 0
    return count >= DEMO_MAX_ROWS


def reset_demo(db: Session, now: datetime | None = None) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            # random password nobody knows, so the regular login form is a dead end
            password_hash=hash_password(secrets.token_urlsafe(32)),
            display_name="Demo",
        )
        db.add(user)
    user.is_demo = True
    user.timezone = DEMO_TIMEZONE
    user.weekly_goal = 10
    user.ghost_after_days = 14
    user.display_name = "Demo"
    db.flush()

    db.execute(delete(Application).where(Application.user_id == user.id))
    # stale demo sessions can go too; anyone mid-visit just clicks the button again
    db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user.id, AuthSession.expires_at < (now or datetime.now(UTC))
        )
    )
    db.commit()
    today = user_today(DEMO_TIMEZONE, now)
    # new seed every day so the demo doesn't look frozen in time
    insert_fake(db, user.id, DEMO_ROWS, seed=today.toordinal(), today=today, days_back=75)
    return user
