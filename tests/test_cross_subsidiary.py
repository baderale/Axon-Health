"""End-to-end: Clinical Research -> gatekeeper -> Pharma -> gatekeeper -> back.

Requires a running NATS JetStream broker (``docker compose up -d nats``). The
interceptor and both subsidiary runtimes run in-process on real NATS; the
Tier-2 judges and the department models are stubbed, so no Ollama is needed.
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import AsyncExitStack
from functools import partial

import pytest

from axon.bus.nats_client import decode_json, ensure_streams, session, subscribe
from axon.bus.subjects import Subjects
from axon.gatekeeper import compliance_agent, hipaa_agent, interceptor
from axon.gatekeeper.verdict import Decision, Severity, Tier, Verdict
from axon.subsidiaries import clinical_research, pharma
from axon.subsidiary import department as department_mod
from axon.subsidiary.runtime import SubsidiaryRuntime

pytestmark = [pytest.mark.usefixtures("require_nats")]

CASE = (
    "Patient_id 12345, MRN MRN-AX-99182, 58 y/o with hepatic impairment. "
    "What is the safe dosing window for acetaminophen?"
)


def _verdict(decision: Decision, tier: Tier, **kw) -> Verdict:
    return Verdict(decision=decision, tier=tier, rationale=f"stub {decision.value}", **kw)


@pytest.fixture
def judges(monkeypatch):
    state = {
        "hipaa": _verdict(Decision.ALLOW, Tier.TIER2_HIPAA),
        "compliance": _verdict(Decision.ALLOW, Tier.TIER2_COMPLIANCE),
    }

    async def hipaa(_request):
        return state["hipaa"]

    async def compliance(_request):
        return state["compliance"]

    monkeypatch.setattr(hipaa_agent, "evaluate", hipaa)
    monkeypatch.setattr(compliance_agent, "evaluate", compliance)
    return state


@pytest.fixture
def models(monkeypatch):
    replies = {
        "intake.v0": json.dumps(
            {
                "question": "Safe acetaminophen dosing in hepatic impairment?",
                "condition": "hepatic impairment",
                "drug": "acetaminophen",
            }
        ),
        "clinsme.v0": "Keep acetaminophen at or below 2 g/day, per Axon Pharma.",
        "pharma-research.v0": "Limit to 2 g/day in hepatic impairment.",
    }

    class Client:
        def __init__(self, name):
            self.name = name

        def chat(self, user_message, *, extra_context=None):
            return replies[self.name]

    monkeypatch.setattr(department_mod, "get_client", Client)


async def _platform(stack: AsyncExitStack, *, consult_timeout: float = 10.0):
    """Interceptor + both subsidiaries, each on its own connection."""
    nc, js = await stack.enter_async_context(session())
    await ensure_streams(js)
    await interceptor.attach(nc, js)
    for build in (clinical_research.build, pharma.build):
        sub_nc, _ = await stack.enter_async_context(session())
        await SubsidiaryRuntime(build(), consult_timeout=consult_timeout).attach(sub_nc)
    return nc


async def _ask(nc, case: str, timeout: float = 15.0) -> dict:
    msg = await nc.request(
        Subjects.ingress("clinical_research"), json.dumps({"case": case}).encode(), timeout=timeout
    )
    return json.loads(msg.data)


async def test_case_is_redacted_on_the_way_to_pharma_and_answered(judges, models):
    pharma_inbox: list[dict] = []
    audit: list[dict] = []

    async with AsyncExitStack() as stack:
        nc = await _platform(stack)
        tap, _ = await stack.enter_async_context(session())
        await subscribe(tap, Subjects.inbox("pharma"), partial(_append, pharma_inbox))
        await subscribe(tap, Subjects.AUDIT_ALL, partial(_append, audit))
        await tap.flush()

        body = await _ask(nc, CASE)
        await asyncio.sleep(0.3)  # let the audit tap catch the last events

    # 1. A final answer came back, built on Pharma's reply.
    result = body["result"]
    assert result["pharma_consulted"] is True, result
    assert result["pharma_error"] is None
    assert "2 g/day" in result["answer"]

    # 2. Pharma never saw the identifiers.
    [delivered] = pharma_inbox
    assert delivered["redacted"] is True
    raw = json.dumps(delivered["payload"])
    assert "12345" not in raw and "MRN-AX-99182" not in raw

    # 3. Pharma's reply crossed the gatekeeper too, linked to the query.
    conversation = [
        e for e in audit if e["request"]["headers"].get("conversation_id") == body["conversation_id"]
    ]
    published = [e for e in conversation if e["stage"].startswith("interceptor.published")]
    query = next(e for e in published if e["request"]["subject"].endswith(".query"))
    reply = next(e for e in published if e["request"]["subject"].endswith(".reply"))
    assert query["request"]["source_subsidiary"] == "clinical_research"
    assert reply["request"]["source_subsidiary"] == "pharma"
    assert reply["request"]["headers"]["in_reply_to"] == query["trace_id"]


async def test_coach_verdict_reaches_clinical_sme_without_hanging(judges, models):
    judges["compliance"] = _verdict(
        Decision.COACH,
        Tier.TIER2_COMPLIANCE,
        severity=Severity.MEDIUM,
        coaching_message="Ask without identifiers.",
    )

    async with AsyncExitStack() as stack:
        # A long consult timeout proves the verdict, not the timeout, ends the wait.
        nc = await _platform(stack, consult_timeout=60.0)
        started = time.monotonic()
        body = await _ask(nc, CASE)
        elapsed = time.monotonic() - started

    result = body["result"]
    assert result["pharma_consulted"] is False
    assert result["pharma_error"]["decision"] == "coach"
    assert result["pharma_error"]["coaching_message"] == "Ask without identifiers."
    assert "No dosing guidance" in result["answer"]
    assert elapsed < 10


async def test_block_on_the_reply_leg_also_fails_fast(judges, models, monkeypatch):
    # Allow the query, block the answer coming back.
    async def hipaa(request):
        if request.subject.endswith(".reply"):
            return _verdict(Decision.BLOCK, Tier.TIER2_HIPAA, severity=Severity.HIGH)
        return _verdict(Decision.ALLOW, Tier.TIER2_HIPAA)

    monkeypatch.setattr(hipaa_agent, "evaluate", hipaa)

    async with AsyncExitStack() as stack:
        nc = await _platform(stack, consult_timeout=60.0)
        started = time.monotonic()
        body = await _ask(nc, CASE)
        elapsed = time.monotonic() - started

    error = body["result"]["pharma_error"]
    assert error["decision"] == "block"
    assert error["incident_id"]
    assert elapsed < 10


async def _append(into: list, msg) -> None:
    into.append(decode_json(msg))
