"""Stuff a bunch of fake applications into an existing account so you can
poke at the UI with real volume.

    .venv/bin/python benchmarks/seed.py you@example.com 10000
"""

import argparse
from datetime import date

from sqlalchemy import select, text

import _setup  # noqa: F401

from app.db import SessionLocal
from app.models.user import User
from app.services.fake_data import insert_fake


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("count", type=int)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    db = SessionLocal()
    user = db.scalar(select(User).where(User.email == args.email))
    if user is None:
        raise SystemExit(f"no account for {args.email}, sign up first")
    added = insert_fake(db, user.id, args.count, seed=args.seed, today=date.today())
    db.execute(text("ANALYZE applications"))
    db.execute(text("ANALYZE status_events"))
    db.commit()
    print(f"added {added:,} fake applications to {args.email}")


if __name__ == "__main__":
    main()
