from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Naive UTC datetime - the storage convention for every timestamp
    column in this schema.

    SQLite has no native timezone-aware datetime type: a DateTime(timezone=
    True) column round-trips through it as naive, so comparing a freshly
    loaded row's timestamp against `datetime.now(timezone.utc)` raises
    "can't compare offset-naive and offset-aware datetimes". Rather than
    special-case SQLite vs PostgreSQL, every timestamp column in this
    schema is plain `DateTime` (naive) and every value written to it comes
    from this function, so naive-UTC is consistent on both backends.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
