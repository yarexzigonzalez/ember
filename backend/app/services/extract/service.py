"""Cache -> LLM -> heuristic, in that order.

Only LLM results get cached. Heuristic is free to rerun, and caching it would
mean a paste that got the fallback once would never get the real model later.
"""

import hashlib
import logging
from functools import lru_cache
from typing import Literal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.extraction_cache import ExtractionCache
from app.services.extract.heuristic import HeuristicExtractor
from app.services.extract.protocol import ExtractedJob, ExtractionFailed, JobExtractor

logger = logging.getLogger("ember.extract")

Via = Literal["cache", "llm", "heuristic"]

_heuristic = HeuristicExtractor()


def input_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def default_llm() -> JobExtractor | None:
    if not settings.anthropic_api_key:
        return None
    import anthropic

    from app.services.extract.anthropic_provider import AnthropicExtractor

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.anthropic_timeout_seconds,
        max_retries=1,
    )
    return AnthropicExtractor(client, settings.anthropic_model)


def extract_job(
    db: Session, text: str, llm: JobExtractor | None, *, allow_llm: bool = True
) -> tuple[ExtractedJob, Via]:
    key = input_hash(text)
    if llm is not None and allow_llm:
        cached = db.get(ExtractionCache, key)
        if cached is not None:
            try:
                return ExtractedJob.model_validate(cached.result), "cache"
            except ValueError:
                pass  # schema moved on since this was cached, just redo it
        try:
            job = llm.extract(text)
        except ExtractionFailed as error:
            logger.info("llm extract fell back to heuristic: %s", error)
        else:
            db.execute(
                insert(ExtractionCache)
                .values(input_hash=key, result=job.model_dump(), model=llm.name)
                .on_conflict_do_update(
                    index_elements=["input_hash"],
                    set_={"result": job.model_dump(), "model": llm.name},
                )
            )
            db.commit()
            return job, "llm"
    return _heuristic.extract(text), "heuristic"
