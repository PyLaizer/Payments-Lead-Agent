"""Domain models shared across ingestion, evaluation and notification.

Two models live here:

* :class:`JobPosting` is the normalized form of a posting from any source.
* :class:`PaymentLeadEvaluation` is the strict structured output expected from the LLM.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobSource(StrEnum):
    """Origin of a job posting."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    HACKER_NEWS = "hackernews"


def _clean_str_list(values: list[str]) -> list[str]:
    """Strip whitespace, drop blanks and remove case-insensitive duplicates, keeping order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = value.strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)
    return cleaned


class JobPosting(BaseModel):
    """A single job posting normalized from any supported source."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    source: JobSource
    external_id: Annotated[str, Field(min_length=1)]
    company: Annotated[str, Field(min_length=1)]
    title: str = ""
    url: str
    description: Annotated[str, Field(min_length=1)]
    posted_at: datetime

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute http(s) URL")
        return value

    @field_validator("posted_at")
    @classmethod
    def _normalize_posted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("posted_at must be timezone-aware")
        return value.astimezone(UTC)

    @property
    def dedup_key(self) -> str:
        """Stable identifier used to avoid alerting on the same posting twice."""
        return f"{self.source.value}:{self.external_id}"

    def is_recent(self, now: datetime, max_age_days: int) -> bool:
        """Return True if the posting is no older than ``max_age_days`` as of ``now``.

        Postings dated in the future (clock skew) are treated as recent.
        """
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        return now.astimezone(UTC) - self.posted_at <= timedelta(days=max_age_days)


class PaymentLeadEvaluation(BaseModel):
    """Structured LLM verdict on whether a posting signals a payment-idempotency lead."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    company_name: str = Field(description="Name of the hiring company.")
    is_relevant: bool = Field(
        description=(
            "True ONLY if the role involves backend/core payment, billing or "
            "transaction infrastructure."
        )
    )
    urgency_score: int = Field(
        ge=1, le=10, description="1 (no signal) to 10 (strong, urgent idempotency need)."
    )
    tech_stack: list[str] = Field(
        description='Technologies mentioned, e.g. ["NestJS", "PostgreSQL", "Redis", "Stripe"].'
    )
    detected_pain_points: list[str] = Field(
        description='Problems implied by the text, e.g. "Duplicate webhooks", "Race conditions".'
    )
    outreach_hook: str = Field(
        description=(
            "1-2 sentence technical pitch on solving their idempotency/race-condition "
            "problem. May be empty when the posting is not relevant."
        )
    )

    @field_validator("tech_stack", "detected_pain_points")
    @classmethod
    def _normalize_lists(cls, value: list[str]) -> list[str]:
        return _clean_str_list(value)

    @field_validator("company_name")
    @classmethod
    def _company_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("company_name must not be blank")
        return value

    def should_alert(self, threshold: int) -> bool:
        """Return True when this evaluation qualifies for a notification."""
        return self.is_relevant and self.urgency_score >= threshold


def parse_evaluation(payload: Any) -> PaymentLeadEvaluation:
    """Validate a raw payload (dict or JSON string) into a :class:`PaymentLeadEvaluation`.

    Raises:
        pydantic.ValidationError: if the payload does not satisfy the schema.
    """
    if isinstance(payload, str | bytes | bytearray):
        return PaymentLeadEvaluation.model_validate_json(payload)
    return PaymentLeadEvaluation.model_validate(payload)
