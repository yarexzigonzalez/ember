"""One shared Anthropic client, or None when there's no key."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    import anthropic


@lru_cache(maxsize=1)
def anthropic_client() -> "anthropic.Anthropic | None":
    if not settings.anthropic_api_key:
        return None
    import anthropic

    return anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.anthropic_timeout_seconds,
        max_retries=1,
    )
