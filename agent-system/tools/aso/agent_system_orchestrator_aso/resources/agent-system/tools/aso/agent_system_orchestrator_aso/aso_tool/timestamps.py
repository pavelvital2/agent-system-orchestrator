"""Timestamp helpers for ASO runtime writes."""

from __future__ import annotations

from datetime import datetime, timezone


DETERMINISTIC_TIMESTAMP = "2026-05-21T00:00:00Z"


def utc_timestamp(*, deterministic: bool = False) -> str:
    if deterministic:
        return DETERMINISTIC_TIMESTAMP
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
