"""add users.timezone

Revision ID: a1f3c2d9e0b4
Revises: cc9062a71273
Create Date: 2026-11-20 10:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1f3c2d9e0b4"
down_revision: str | None = "cc9062a71273"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("timezone", sa.Text(), server_default="UTC", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "timezone")
