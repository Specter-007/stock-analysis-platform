"""Dialect-portable column types shared by the ORM models."""
from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


def portable_json():
    """A JSON column that renders as native JSONB on PostgreSQL (efficient
    indexing/querying of nested state) and falls back to generic JSON
    (TEXT-backed) on any other dialect, in particular the SQLite backend
    this repo's local dev/test environment actually runs against.
    """
    return JSON().with_variant(JSONB, "postgresql")
