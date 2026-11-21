"""Wipe the demo account and reseed it. Render runs this nightly as a cron job.

    cd backend && python -m scripts.reset_demo
"""

from app.db import SessionLocal
from app.services.demo import reset_demo


def main() -> None:
    db = SessionLocal()
    try:
        user = reset_demo(db)
        print(f"demo reset: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
