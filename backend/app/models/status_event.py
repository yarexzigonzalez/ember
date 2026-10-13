from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class StatusEvent(Base):
    """One row per status change. Analytics (time-to-first-response) reads this table."""

    __tablename__ = "status_events"
    __table_args__ = (
        CheckConstraint(
            "to_status IN ('saved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'ghosted')",
            name="to_status",
        ),
        CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('saved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'ghosted')",
            name="from_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    application: Mapped[Application] = relationship(back_populates="status_events")
    user: Mapped[User] = relationship()
