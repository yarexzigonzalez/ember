"""composite indexes for the hot paths

Revision ID: b7e2d4f1a9c3
Revises: a1f3c2d9e0b4
Create Date: 2026-11-20 14:00:00

Added after the naive versions on purpose so the benchmark has a real
"before". Every one of these leads with user_id because every query in the
app is scoped to one user.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "b7e2d4f1a9c3"
down_revision: str | None = "a1f3c2d9e0b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEXES = [
    ("ix_applications_user_status", "applications", ["user_id", "status"]),
    ("ix_applications_user_applied_at", "applications", ["user_id", "applied_at"]),
    ("ix_applications_user_source", "applications", ["user_id", "source"]),
    # Ghost Radar: open stuff ordered by how long it's been quiet
    ("ix_applications_user_last_status_at", "applications", ["user_id", "last_status_at"]),
    # default list sort
    ("ix_applications_user_updated_at", "applications", ["user_id", "updated_at"]),
    ("ix_status_events_user_occurred_at", "status_events", ["user_id", "occurred_at"]),
]


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)
    # (user_id, dedupe_key) is already covered by the unique constraint.


def downgrade() -> None:
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
