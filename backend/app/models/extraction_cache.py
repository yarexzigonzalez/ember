from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ExtractionCache(Base):
    """LLM extract results keyed by SHA-256 of the pasted job text. Avoids repeat API calls."""

    __tablename__ = "extraction_cache"

    input_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
