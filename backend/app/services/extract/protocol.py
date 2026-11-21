from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator

Seniority = Literal["intern", "new_grad", "junior", "mid", "senior", "unknown"]
RoleType = Literal["intern", "full_time", "contract", "unknown"]


class ExtractedJob(BaseModel):
    """What any extractor has to hand back. Same shape whether it came from a model or regex."""

    company: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    posting_url: str | None = Field(default=None, max_length=2000)
    seniority: Seniority = "unknown"
    role_type: RoleType = "unknown"
    requirements: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("company", "role", "location", "posting_url")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("requirements")
    @classmethod
    def tidy_requirements(cls, value: list[str]) -> list[str]:
        return [" ".join(item.split())[:300] for item in value if item and item.strip()][:15]


class ExtractionFailed(Exception):
    """Provider couldn't produce something usable. Caller falls back."""


class JobExtractor(Protocol):
    """Anything with a name and an extract(). Tests swap in fakes, prod swaps in Anthropic."""

    name: str

    def extract(self, text: str) -> ExtractedJob: ...
