from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

VALID_CATEGORIES = ("ACCOUNT", "BILLING_QUESTION", "BUG_REPORT", "DATA_ISSUE", "FEATURE_REQUEST", "OTHER")


class ContactRequest(BaseModel):
    contact_email: EmailStr
    category: str
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v

    @field_validator("subject", "message")
    @classmethod
    def _strip_and_require_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be blank.")
        return v


class ContactResponse(BaseModel):
    id: str
    created_at: datetime
    message: str
