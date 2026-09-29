"""Integration tests for the gatekeeper interceptor pipeline.

Requires a running NATS JetStream broker (``docker compose up -d nats``).
Tier-2 LLM judges are monkeypatched so these tests do not require Ollama.
"""

from __future__ import annotations

import asyncio

import pytest

from axon.bus.nats_client import (
    decode_json,
    ensure_streams,
    publish_json,
    session,
    subscribe,
)
from axon.bus.subjects import Subjects
from axon.gatekeeper import compliance_agent, hipaa_agent
from axon.gatekeeper.interceptor import handle_request
from axon.gatekeeper.verdict import (
    Decision,
    GatekeeperRequest,
    Severity,
    Tier,
    Verdict,
)


pytestmark = [pytest.mark.usefixtures("require_nats")]


def _make_request(payload: dict, **overrides) -> GatekeeperRequest:
    base = dict(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.research.query",
        payload=payload,
    )
    base.update(overrides)
    return GatekeeperRequest(**base)


def _stub_verdict(decision: Decision, *, tier: Tier, severity: Severity = Severity.LOW) -> Verdict:
    return Verdict(
        decision=decision,
        severity=severity,
        tier=tier,
        rationale=f"stub {tier.value} -> {decision.value}",
    )


@pytest.fixture
def stub_judges(monkeypatch):
    """Replace the Tier-2 judges with synchronous stubs configurable per test."""
    state = {
        "hipaa": _stub_verdict(Decision.ALLOW, tier=Tier.TIER2_HIPAA),
        "compliance": _stub_verdict(Decision.ALLOW, tier=Tier.TIER2_COMPLIANCE),
    }

    async def stub_hipaa(_request):
        return state["hipaa"]

    async def stub_compliance(_request):
        return state["compliance"]

    monkeypatch.setattr(hipaa_agent, "evaluate", stub_hipaa)
    monkeypatch.setattr(compliance_agent, "evaluate", stub_compliance)
    return state


async def _collect(nc, subject: str, *, until: asyncio.Event, into: list) -> None:
    async def cb(msg):
        into.append(decode_json(msg))
        until.set()

    await subscribe(nc, subject, cb)


async def test_clean_cross_subsidiary_message_is_forwarded(stub_judges):
    request = _make_request({"question": "What is the standard adult dose of acetaminophen?"})

    forwarded: list[dict] = []
    got_forwarded = asyncio.Event()

    async with session() as (nc, js):
        await ensure_streams(js)
        await _collect(nc, Subjects.inbox("pharma"), until=got_forwarded, into=forwarded)
        await handle_request(nc, js, request)
        try:
            await asyncio.wait_for(got_forwarded.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass

    assert forwarded, "Expected the clean payload to be forwarded to the pharma inbox"
    assert forwarded[0]["payload"]["question"].startswith("What is the standard")
    assert forwarded[0]["redacted"] is False


async def test_phi_payload_is_redacted_before_forwarding(stub_judges):
    request = _make_request(
        {
            "patient_id": "12345",
            "question": "For patient_id 12345, what is the safe dose?",
        }
    )

    forwarded: list[dict] = []
    got = asyncio.Event()

    async with session() as (nc, js):
        await ensure_streams(js)
        await _collect(nc, Subjects.inbox("pharma"), until=got, into=forwarded)
        await handle_request(nc, js, request)
        try:
            await asyncio.wait_for(got.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass

    assert forwarded, "Expected the redacted payload to be forwarded"
    payload = forwarded[0]["payload"]
    assert payload["patient_id"] == "[REDACTED]"
    assert "12345" not in payload["question"]
    assert forwarded[0]["redacted"] is True


async def test_tier2_judges_see_the_tier1_redacted_payload(monkeypatch):
    seen: list[dict] = []

    async def recording_judge(judged_request):
        seen.append(judged_request.payload)
        return _stub_verdict(Decision.ALLOW, tier=Tier.TIER2_HIPAA)

    monkeypatch.setattr(hipaa_agent, "evaluate", recording_judge)
    monkeypatch.setattr(compliance_agent, "evaluate", recording_judge)

    request = _make_request(
        {"mrn": "MRN-AX-99182", "question": "For MRN MRN-AX-99182, what is the safe dose?"}
    )
    async with session() as (nc, js):
        await ensure_streams(js)
        await handle_request(nc, js, request)

    assert len(seen) == 2, "Expected both judges to run"
    for payload in seen:
        assert "MRN-AX-99182" not in str(payload)


async def test_egress_attempt_is_blocked_and_opens_incident(stub_judges):
    request = _make_request(
        {
            "email_to": "outside@gmail.com",
            "body": "patient record attached",
        },
        subject="axon.clinical_research.pharma.email.send",
    )

    verdicts: list[dict] = []
    incidents: list[dict] = []
    got_verdict = asyncio.Event()
    got_incident = asyncio.Event()

    async with session() as (nc, js):
        await ensure_streams(js)
        await _collect(nc, Subjects.GATEKEEPER_VERDICT, until=got_verdict, into=verdicts)
        await _collect(nc, Subjects.INCIDENT_ALL, until=got_incident, into=incidents)
        await handle_request(nc, js, request)
        try:
            await asyncio.wait_for(
                asyncio.gather(got_verdict.wait(), got_incident.wait()), timeout=5.0
            )
        except asyncio.TimeoutError:
            pass

    assert verdicts, "Expected a BLOCK verdict to be announced"
    assert verdicts[0]["trace_id"] == request.trace_id
    assert verdicts[0]["verdict"]["decision"] == "block"
    assert verdicts[0]["verdict"]["severity"] == "high"
    assert verdicts[0]["verdict"]["incident_id"] is not None

    assert incidents, "Expected an incident on INCIDENT.*"
    assert incidents[0]["status"] == "open"
    assert incidents[0]["verdict"]["decision"] == "block"


async def test_tier2_hipaa_can_override_tier1_allow_to_block(stub_judges):
    stub_judges["hipaa"] = _stub_verdict(
        Decision.BLOCK, tier=Tier.TIER2_HIPAA, severity=Severity.HIGH
    )

    request = _make_request({"question": "Innocuous looking but flagged by judge."})

    verdicts: list[dict] = []
    got = asyncio.Event()
    async with session() as (nc, js):
        await ensure_streams(js)
        await _collect(nc, Subjects.GATEKEEPER_VERDICT, until=got, into=verdicts)
        await handle_request(nc, js, request)
        try:
            await asyncio.wait_for(got.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass

    assert verdicts
    assert verdicts[0]["verdict"]["decision"] == "block"
    assert verdicts[0]["verdict"]["severity"] == "high"


async def test_tier2_compliance_can_coach(stub_judges):
    stub_judges["compliance"] = Verdict(
        decision=Decision.COACH,
        severity=Severity.MEDIUM,
        tier=Tier.TIER2_COMPLIANCE,
        rationale="Borderline marketing claim.",
        coaching_message="Please clarify whether this is internal scientific discussion.",
    )

    request = _make_request({"question": "Could this drug help in an off-label use?"})

    verdicts: list[dict] = []
    got = asyncio.Event()
    forwarded: list[dict] = []
    no_forward_yet = asyncio.Event()

    async with session() as (nc, js):
        await ensure_streams(js)
        await _collect(nc, Subjects.GATEKEEPER_VERDICT, until=got, into=verdicts)
        await _collect(nc, Subjects.inbox("pharma"), until=no_forward_yet, into=forwarded)
        await handle_request(nc, js, request)
        try:
            await asyncio.wait_for(got.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass
        await asyncio.sleep(0.2)

    assert verdicts and verdicts[0]["verdict"]["decision"] == "coach"
    assert not forwarded, "COACH must not forward the payload"
