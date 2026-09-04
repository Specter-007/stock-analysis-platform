from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.validation import normalize_and_validate_ticker

VALID_THEMES = ("dark", "light")


class PreferencesResponse(BaseModel):
    timezone: str
    default_benchmark: str
    theme: str
    email_notifications_enabled: bool
    research_notifications_enabled: bool
    marketing_consent: bool
    terms_accepted_at: datetime | None
    privacy_accepted_at: datetime | None
    onboarding_completed: bool
    onboarding_completed_at: datetime | None


class UpdatePreferencesRequest(BaseModel):
    timezone: str | None = Field(default=None, max_length=64)
    default_benchmark: str | None = Field(default=None, max_length=12)
    theme: str | None = None
    email_notifications_enabled: bool | None = None
    research_notifications_enabled: bool | None = None
    marketing_consent: bool | None = None

    @field_validator("default_benchmark")
    @classmethod
    def _valid_ticker(cls, v: str | None) -> str | None:
        return normalize_and_validate_ticker(v) if v is not None else None

    @field_validator("theme")
    @classmethod
    def _valid_theme(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_THEMES:
            raise ValueError(f"theme must be one of {VALID_THEMES}")
        return v

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {v!r}") from exc
        return v
