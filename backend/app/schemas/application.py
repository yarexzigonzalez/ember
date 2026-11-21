import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ApplicationStatus

SortField = Literal["updated_at", "company", "role", "status", "applied_at"]
SortDirection = Literal["asc", "desc"]


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=80)
    posting_url: str | None = Field(default=None, max_length=2000)
    status: ApplicationStatus = ApplicationStatus.SAVED
    seniority: str | None = Field(default=None, max_length=40)
    role_type: str | None = Field(default=None, max_length=40)
    requirements: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=8000)
    applied_at: date | None = None

    @field_validator("requirements")
    @classmethod
    def limit_requirements(cls, value: list[str]) -> list[str]:
        if len(value) > 40:
            raise ValueError("too many requirements")
        cleaned = [item.strip()[:300] for item in value if item.strip()]
        return cleaned


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=80)
    posting_url: str | None = Field(default=None, max_length=2000)
    status: ApplicationStatus | None = None
    seniority: str | None = Field(default=None, max_length=40)
    role_type: str | None = Field(default=None, max_length=40)
    requirements: list[str] | None = None
    notes: str | None = Field(default=None, max_length=8000)
    applied_at: date | None = None

    @field_validator("requirements")
    @classmethod
    def limit_requirements(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(value) > 40:
            raise ValueError("too many requirements")
        return [item.strip()[:300] for item in value if item.strip()]


class ApplicationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: str
    role: str
    location: str | None
    source: str | None
    posting_url: str | None
    status: str
    seniority: str | None
    role_type: str | None
    requirements: list[str]
    notes: str | None
    applied_at: date | None
    last_status_at: datetime
    created_at: datetime
    updated_at: datetime


class ApplicationList(BaseModel):
    items: list[ApplicationPublic]
    total: int
    page: int
    page_size: int


class ApplicationListParams(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    status: ApplicationStatus | None = None
    source: str | None = Field(default=None, max_length=80)
    sort: SortField = "updated_at"
    direction: SortDirection = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
