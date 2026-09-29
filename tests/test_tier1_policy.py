"""Unit tests for the Tier-1 deterministic policy engine.

These tests do not require any infrastructure (no NATS, no Ollama). They
exercise the four verdict paths that Tier-1 alone can produce: ALLOW,
ALLOW+escalate (boundary crossing), REDACT, BLOCK.
"""

from __future__ import annotations

import pytest

from axon.gatekeeper import tier1_policy
from axon.gatekeeper.verdict import Decision, GatekeeperRequest, Severity, Tier


def _request(**overrides):
    base = dict(
        source_subsidiary="clinical_research",
        target_subsidiary="clinical_research",
        subject="axon.clinical_research.clinical_research.compliance_dept.check",
        payload={"question": "is this OK?"},
    )
    base.update(overrides)
    return GatekeeperRequest(**base)


def test_intra_subsidiary_clean_payload_allows_without_escalation():
    verdict = tier1_policy.evaluate(_request())
    assert verdict.decision is Decision.ALLOW
    assert verdict.tier is Tier.TIER1
    assert "escalate" not in verdict.matched_rules


def test_cross_subsidiary_clean_payload_allows_with_escalation():
    verdict = tier1_policy.evaluate(
        _request(target_subsidiary="pharma", subject="axon.clinical_research.pharma.research.query")
    )
    assert verdict.decision is Decision.ALLOW
    assert "escalate" in verdict.matched_rules
    assert "boundary.cross_subsidiary" in verdict.matched_rules


def test_phi_field_triggers_redact():
    verdict = tier1_policy.evaluate(
        _request(
            target_subsidiary="pharma",
            payload={"patient_id": "12345", "question": "dosing for hepatic impairment?"},
        )
    )
    assert verdict.decision is Decision.REDACT
    assert verdict.redacted_payload is not None
    assert verdict.redacted_payload["patient_id"] == "[REDACTED]"
    assert "escalate" in verdict.matched_rules  # we always escalate after redact


def test_phi_pattern_in_freetext_triggers_redact():
    verdict = tier1_policy.evaluate(
        _request(
            target_subsidiary="pharma",
            payload={
                "question": "For patient_id 12345 with hepatic impairment, what is the dose?",
            },
        )
    )
    assert verdict.decision is Decision.REDACT
    assert "[REDACTED:patient_id]" in verdict.redacted_payload["question"]


def test_ssn_pattern_redacted():
    verdict = tier1_policy.evaluate(
        _request(
            target_subsidiary="pharma",
            payload={"note": "history mentions SSN 123-45-6789"},
        )
    )
    assert verdict.decision is Decision.REDACT
    assert "[REDACTED:ssn]" in verdict.redacted_payload["note"]


def test_external_email_address_blocks_high_severity():
    verdict = tier1_policy.evaluate(
        _request(
            target_subsidiary="pharma",
            subject="axon.clinical_research.pharma.email.send",
            payload={
                "email_to": "outside@gmail.com",
                "body": "see attached",
            },
        )
    )
    assert verdict.decision is Decision.BLOCK
    assert verdict.severity is Severity.HIGH
    assert any(r.startswith("egress.") for r in verdict.matched_rules)


def test_external_url_in_webhook_blocks():
    verdict = tier1_policy.evaluate(
        _request(
            target_subsidiary="pharma",
            payload={
                "webhook": "https://attacker.example.com/exfil",
                "body": "record",
            },
        )
    )
    assert verdict.decision is Decision.BLOCK


def test_internal_email_address_does_not_block():
    verdict = tier1_policy.evaluate(
        _request(
            target_subsidiary="pharma",
            payload={
                "email_to": "service-account@axonhealth.internal",
                "body": "ok",
            },
        )
    )
    assert verdict.decision is not Decision.BLOCK


def test_subject_verb_indicating_egress_blocks_even_without_external_address():
    verdict = tier1_policy.evaluate(
        _request(
            subject="axon.clinical_research.pharma.send.payload",
            target_subsidiary="pharma",
            payload={"body": "anything"},
        )
    )
    assert verdict.decision is Decision.BLOCK


def test_egress_verb_in_final_subject_segment_blocks():
    # axon.{source}.{target}.{dept}.{verb}: "send" sits in the verb slot here.
    verdict = tier1_policy.evaluate(
        _request(
            subject="axon.clinical_research.pharma.research.send",
            target_subsidiary="pharma",
            payload={"body": "anything"},
        )
    )
    assert verdict.decision is Decision.BLOCK
    assert "egress.subject.send" in verdict.matched_rules


def test_reply_verb_is_not_treated_as_egress():
    verdict = tier1_policy.evaluate(
        _request(
            subject="axon.pharma.clinical_research.research.reply",
            source_subsidiary="pharma",
            payload={"answer": "Max 3 g/day in hepatic impairment."},
        )
    )
    assert verdict.decision is Decision.ALLOW


def test_redact_does_not_mutate_original_payload():
    payload = {"patient_id": "12345"}
    request = _request(target_subsidiary="pharma", payload=payload)
    verdict = tier1_policy.evaluate(request)
    assert verdict.decision is Decision.REDACT
    assert payload == {"patient_id": "12345"}  # original untouched
    assert verdict.redacted_payload["patient_id"] == "[REDACTED]"


def test_needs_escalation_flag_is_set_for_redact_and_cross_subsidiary_allow():
    redact = tier1_policy.evaluate(
        _request(target_subsidiary="pharma", payload={"patient_id": "1"})
    )
    cross_allow = tier1_policy.evaluate(
        _request(target_subsidiary="pharma", payload={"q": "hi"})
    )
    intra_allow = tier1_policy.evaluate(_request(payload={"q": "hi"}))

    assert "escalate" in redact.matched_rules
    assert cross_allow.needs_escalation()
    assert not intra_allow.needs_escalation()
