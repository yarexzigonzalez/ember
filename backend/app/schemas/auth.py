import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.calendar import is_valid_timezone


def _check_timezone(value: str | None) -> str | None:
    if value is not None and not is_valid_timezone(value):
        raise ValueError("unknown timezone, use an IANA name like America/Chicago")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)
    # The browser sends Intl's guess. Falls back to UTC if it doesn't.
    timezone: str | None = Field(default=None, max_length=64)

    _tz = field_validator("timezone")(_check_timezone)


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)


class SettingsUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)
    weekly_goal: int | None = Field(default=None, ge=1, le=100)
    ghost_after_days: int | None = Field(default=None, ge=1, le=120)

    _tz = field_validator("timezone")(_check_timezone)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    timezone: str
    is_demo: bool
    weekly_goal: int
    ghost_after_days: int
    created_at: datetime
