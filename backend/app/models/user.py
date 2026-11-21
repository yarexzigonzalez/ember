from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.session import Session


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    # IANA name like America/Los_Angeles. Never a fixed offset, DST would break it.
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    weekly_goal: Mapped[int] = mapped_column(Integer, nullable=False, server_default="12")
    ghost_after_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="14"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # passive_deletes: the FK is ON DELETE CASCADE, so don't null out user_id first.
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )
