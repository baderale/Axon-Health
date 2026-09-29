"""Unit tests for the Tier-2 judge's input and output handling (no LLM needed)."""

from __future__ import annotations

import json

from axon.gatekeeper.judge import _build_user_message, _parse_verdict
from axon.gatekeeper.verdict import Decision, GatekeeperRequest, Severity, Tier


def test_parse_accepts_uppercase_decision_and_severity():
    verdict = _parse_verdict(
        '{"decision": "ALLOW", "severity": "Low", "rationale": "fine"}',
        tier=Tier.TIER2_COMPLIANCE,
    )
    assert verdict.decision is Decision.ALLOW
    assert verdict.severity is Severity.LOW


def test_parse_null_severity_defaults_to_low():
    verdict = _parse_verdict('{"decision": "allow", "severity": null}', tier=Tier.TIER2_HIPAA)
    assert verdict.severity is Severity.LOW


def test_parse_unknown_decision_still_coaches():
    verdict = _parse_verdict('{"decision": "maybe"}', tier=Tier.TIER2_HIPAA)
    assert verdict.decision is Decision.COACH


def test_user_message_describes_a_reply_in_plain_terms():
    request = GatekeeperRequest(
        source_subsidiary="pharma",
        target_subsidiary="clinical_research",
        subject="axon.pharma.clinical_research.research.reply",
        payload={"answer": "2 g/day"},
    )
    exchange = json.loads(_build_user_message(request))["exchange"]
    assert "research department of pharma is answering" in exchange
    assert "clinical_research asked" in exchange
