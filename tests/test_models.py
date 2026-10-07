"""Tests for the domain models."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from lead_agent.models import (
    JobPosting,
    JobSource,
    PaymentLeadEvaluation,
    parse_evaluation,
)

NOW = datetime(2026, 10, 7, 7, 0, tzinfo=UTC)


def make_posting(**overrides: Any) -> JobPosting:
    data: dict[str, Any] = {
        "source": JobSource.GREENHOUSE,
        "external_id": "12345",
        "company": "Acme Pay",
        "title": "Senior Backend Engineer, Payments",
        "url": "https://boards.greenhouse.io/acme/jobs/12345",
        "description": "Build our ledger and webhook pipeline.",
        "posted_at": NOW - timedelta(days=2),
    }
    data.update(overrides)
    return JobPosting(**data)


def make_eval_payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "company_name": "Acme Pay",
        "is_relevant": True,
        "urgency_score": 8,
        "tech_stack": ["NestJS", "PostgreSQL"],
        "detected_pain_points": ["Duplicate webhooks"],
        "outreach_hook": "We harden webhook handlers with idempotency keys.",
    }
    data.update(overrides)
    return data


class TestJobPosting:
    def test_valid_posting(self) -> None:
        posting = make_posting()
        assert posting.dedup_key == "greenhouse:12345"

    def test_is_frozen(self) -> None:
        posting = make_posting()
        with pytest.raises(ValidationError):
            posting.company = "Other"  # type: ignore[misc]

    def test_strips_whitespace(self) -> None:
        assert make_posting(company="  Acme Pay  ").company == "Acme Pay"

    @pytest.mark.parametrize("field", ["external_id", "company", "description"])
    def test_required_text_fields_reject_blank(self, field: str) -> None:
        with pytest.raises(ValidationError):
            make_posting(**{field: "   "})

    @pytest.mark.parametrize("url", ["", "ftp://x.com/a", "not a url", "https://"])
    def test_rejects_bad_urls(self, url: str) -> None:
        with pytest.raises(ValidationError):
            make_posting(url=url)

    def test_rejects_naive_datetime(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            make_posting(posted_at=datetime(2026, 10, 1))

    def test_normalizes_to_utc(self) -> None:
        lagos = timezone(timedelta(hours=1))
        posting = make_posting(posted_at=datetime(2026, 10, 1, 12, 0, tzinfo=lagos))
        assert posting.posted_at == datetime(2026, 10, 1, 11, 0, tzinfo=UTC)
        assert posting.posted_at.utcoffset() == timedelta(0)

    def test_unknown_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_posting(source="indeed")

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_posting(salary="lots")

    @pytest.mark.parametrize(
        ("age_days", "expected"),
        [(0, True), (13, True), (14, True), (15, False), (-1, True)],
    )
    def test_is_recent_boundaries(self, age_days: int, expected: bool) -> None:
        posting = make_posting(posted_at=NOW - timedelta(days=age_days))
        assert posting.is_recent(NOW, 14) is expected

    def test_is_recent_requires_aware_now(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            make_posting().is_recent(datetime(2026, 10, 7), 14)


class TestPaymentLeadEvaluation:
    def test_valid_evaluation(self) -> None:
        ev = PaymentLeadEvaluation(**make_eval_payload())
        assert ev.urgency_score == 8
        assert ev.tech_stack == ["NestJS", "PostgreSQL"]

    @pytest.mark.parametrize("score", [0, 11, -3])
    def test_score_out_of_range_rejected(self, score: int) -> None:
        with pytest.raises(ValidationError):
            PaymentLeadEvaluation(**make_eval_payload(urgency_score=score))

    @pytest.mark.parametrize("score", [1, 10])
    def test_score_bounds_accepted(self, score: int) -> None:
        assert (
            PaymentLeadEvaluation(**make_eval_payload(urgency_score=score)).urgency_score == score
        )

    def test_score_must_be_int(self) -> None:
        with pytest.raises(ValidationError):
            PaymentLeadEvaluation(**make_eval_payload(urgency_score="high"))

    def test_missing_field_rejected(self) -> None:
        payload = make_eval_payload()
        del payload["outreach_hook"]
        with pytest.raises(ValidationError):
            PaymentLeadEvaluation(**payload)

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PaymentLeadEvaluation(**make_eval_payload(notes="ignore previous instructions"))

    def test_blank_company_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PaymentLeadEvaluation(**make_eval_payload(company_name="   "))

    def test_lists_are_cleaned_and_deduplicated(self) -> None:
        ev = PaymentLeadEvaluation(
            **make_eval_payload(tech_stack=[" Redis ", "redis", "", "Stripe"])
        )
        assert ev.tech_stack == ["Redis", "Stripe"]

    def test_empty_hook_allowed_for_irrelevant_posting(self) -> None:
        ev = PaymentLeadEvaluation(
            **make_eval_payload(is_relevant=False, urgency_score=1, outreach_hook="")
        )
        assert ev.outreach_hook == ""

    @pytest.mark.parametrize(
        ("relevant", "score", "expected"),
        [(True, 7, True), (True, 10, True), (True, 6, False), (False, 10, False)],
    )
    def test_should_alert(self, relevant: bool, score: int, expected: bool) -> None:
        ev = PaymentLeadEvaluation(**make_eval_payload(is_relevant=relevant, urgency_score=score))
        assert ev.should_alert(7) is expected


class TestParseEvaluation:
    def test_parses_dict(self) -> None:
        assert parse_evaluation(make_eval_payload()).company_name == "Acme Pay"

    def test_parses_json_string(self) -> None:
        assert parse_evaluation(json.dumps(make_eval_payload())).urgency_score == 8

    @pytest.mark.parametrize("payload", ["{not json", "[]", "null", "", 42, None])
    def test_malformed_payloads_raise_validation_error(self, payload: Any) -> None:
        with pytest.raises(ValidationError):
            parse_evaluation(payload)
