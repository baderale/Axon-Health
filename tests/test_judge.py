"""Unit tests for the Tier-2 judge's input and output handling (no LLM needed)."""

from __future__ import annotations

import json

from axon.gatekeeper.interceptor import _combine_for_redact
from axon.gatekeeper.judge import _build_user_message, _parse_verdict
from axon.gatekeeper.verdict import Decision, GatekeeperRequest, Severity, Tier, Verdict
from axon.tools import judge_eval


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


def test_parse_reads_reject_as_block():
    verdict = _parse_verdict('{"decision": "REJECT"}', tier=Tier.TIER2_COMPLIANCE)
    assert verdict.decision is Decision.BLOCK


def test_fail_safe_verdicts_are_tagged():
    verdict = _parse_verdict("not json at all", tier=Tier.TIER2_HIPAA)
    assert verdict.decision is Decision.COACH
    assert verdict.matched_rules == ["judge.parse_failed"]


def _cross_request(payload: dict) -> GatekeeperRequest:
    return GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.research.query",
        payload=payload,
    )


def test_a_judge_redact_is_sent_back_not_delivered():
    request = _cross_request({"question": "spoke w/ daughter priya re: INR 5.2"})
    tier1 = Verdict(decision=Decision.ALLOW, tier=Tier.TIER1, rationale="clean", matched_rules=["escalate"])
    rewrite = Verdict(
        decision=Decision.REDACT,
        tier=Tier.TIER2_HIPAA,
        rationale="A relative's name remains.",
        redacted_payload={"question": "spoke w/ daughter re: [REDACTED:lab_value]"},
    )
    allow = Verdict(decision=Decision.ALLOW, tier=Tier.TIER2_COMPLIANCE, rationale="ok")

    final, _ = _combine_for_redact(request, tier1, [rewrite, allow])

    assert final.decision is Decision.COACH
    assert final.redacted_payload is None
    assert "tier2.redact_means_coach" in final.matched_rules
    assert "relative" in final.coaching_message


def test_only_the_tier1_redaction_is_delivered():
    request = _cross_request({"question": "MRN 4471-209, apixaban 5 mg BID?"})
    tier1_payload = {"question": "MRN [REDACTED:mrn], apixaban 5 mg BID?"}
    tier1 = Verdict(
        decision=Decision.REDACT,
        tier=Tier.TIER1,
        rationale="mrn",
        redacted_payload=tier1_payload,
        matched_rules=["phi.pattern.mrn", "escalate"],
    )
    allow_h = Verdict(decision=Decision.ALLOW, tier=Tier.TIER2_HIPAA, rationale="ok")
    allow_c = Verdict(decision=Decision.ALLOW, tier=Tier.TIER2_COMPLIANCE, rationale="ok")

    final, payload = _combine_for_redact(request, tier1, [allow_h, allow_c])

    assert final.decision is Decision.REDACT
    assert payload == tier1_payload


def test_judge_eval_sets_are_well_formed():
    for name in judge_eval.SETS:
        cases = judge_eval.load(name)
        assert cases, f"{name} is empty"
        for case in cases:
            assert case["hipaa"] in ("pass", "stop") and case["compliance"] in ("pass", "stop")
            judge_eval.request_for(case)  # a cross-subsidiary subject
            text = "\n".join(str(v) for v in case["payload"].values())
            for s in case["residual"] + case["keep"]:
                assert s in text, f"{case['id']}: {s!r} is not in the payload"
            assert bool(case["residual"]) == (case["hipaa"] == "stop"), case["id"]
