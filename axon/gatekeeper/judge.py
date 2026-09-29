"""Shared LangGraph judge factory used by HIPAA Agent and Compliance Agent.

Both judges have the same shape: retrieve relevant rules from the configured
corpus, then ask an LLM to return a structured verdict. They differ only in
their Model Registry entry (system prompt + retrieval profile).
"""

from __future__ import annotations

import json
import re
from typing import TypedDict

import structlog
from langgraph.graph import END, START, StateGraph

from axon.bus.subjects import Subjects
from axon.gatekeeper.retrieval import retrieve
from axon.gatekeeper.verdict import (
    Decision,
    GatekeeperRequest,
    Severity,
    Tier,
    Verdict,
)
from axon.model_registry import get_client
from axon.model_registry.registry import resolve

log = structlog.get_logger(__name__)


class JudgeState(TypedDict, total=False):
    request: GatekeeperRequest
    retrieved_context: str
    verdict: Verdict


def _make_query(request: GatekeeperRequest) -> str:
    payload_str = json.dumps(request.payload, default=str)
    return f"{request.subject} {payload_str}"


def _describe_exchange(request: GatekeeperRequest) -> str | None:
    """Plain-language reading of the subject, so the judge need not parse it."""
    parsed = Subjects.parse_cross_subsidiary(request.subject)
    if parsed is None:
        return None
    source, target, dept, verb = parsed
    if verb == "reply":
        return (
            f"The {dept} department of {source} is answering a question that "
            f"{target} asked it (internal exchange between Axon Health subsidiaries)."
        )
    return (
        f"{source} is sending a '{verb}' to the {dept} department of {target} "
        "(internal exchange between Axon Health subsidiaries)."
    )


def _build_user_message(request: GatekeeperRequest) -> str:
    return json.dumps(
        {
            "source_subsidiary": request.source_subsidiary,
            "target_subsidiary": request.target_subsidiary,
            "subject": request.subject,
            "exchange": _describe_exchange(request),
            "payload": request.payload,
        },
        indent=2,
        default=str,
    )


_BRACE_JSON = re.compile(r"\{[\s\S]*\}")


def _parse_verdict(text: str, *, tier: Tier) -> Verdict:
    """Parse the model's JSON output into a Verdict. Forgiving."""
    match = _BRACE_JSON.search(text)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("judge.parse_failed", text=text[:400])
        return Verdict(
            decision=Decision.COACH,
            severity=Severity.MEDIUM,
            tier=tier,
            rationale="Judge returned unparseable output; coaching the caller to retry.",
            coaching_message="Internal judge parse error; please retry.",
        )

    try:
        # Small models often answer "ALLOW" / "High"; the schema is lowercase.
        return Verdict(
            decision=Decision(str(data["decision"]).strip().lower()),
            severity=Severity(str(data.get("severity") or "low").strip().lower()),
            tier=tier,
            rationale=data.get("rationale", ""),
            coaching_message=data.get("coaching_message"),
            redacted_payload=data.get("redacted_payload"),
        )
    except (KeyError, ValueError) as exc:
        log.warning("judge.schema_invalid", error=str(exc), raw=raw[:400])
        return Verdict(
            decision=Decision.COACH,
            severity=Severity.MEDIUM,
            tier=tier,
            rationale=f"Judge output failed schema validation: {exc}",
            coaching_message="Internal judge schema error; please retry.",
        )


def build_judge_graph(logical_model: str):
    """Return a compiled LangGraph judge for the given Model Registry entry."""
    spec = resolve(logical_model)
    tier = Tier.TIER2_HIPAA if "hipaa" in logical_model else Tier.TIER2_COMPLIANCE

    def retrieve_node(state: JudgeState) -> JudgeState:
        request = state["request"]
        ctx = ""
        if spec.retrieval_profile:
            ctx = retrieve(spec.retrieval_profile, _make_query(request))
        return {"retrieved_context": ctx}

    def judge_node(state: JudgeState) -> JudgeState:
        request = state["request"]
        client = get_client(logical_model)
        try:
            text = client.chat(
                _build_user_message(request),
                extra_context=state.get("retrieved_context") or None,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("judge.llm_error", error=str(exc), logical_model=logical_model)
            return {
                "verdict": Verdict(
                    decision=Decision.COACH,
                    severity=Severity.MEDIUM,
                    tier=tier,
                    rationale=f"Judge LLM unavailable: {exc}",
                    coaching_message="Internal LLM error; please retry.",
                )
            }
        return {"verdict": _parse_verdict(text, tier=tier)}

    graph: StateGraph = StateGraph(JudgeState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("judge", judge_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "judge")
    graph.add_edge("judge", END)
    return graph.compile()


async def judge(logical_model: str, request: GatekeeperRequest) -> Verdict:
    """Run the configured LangGraph judge against a request, return its Verdict."""
    compiled = build_judge_graph(logical_model)
    final_state = await compiled.ainvoke({"request": request})
    verdict = final_state.get("verdict")
    if verdict is None:
        return Verdict(
            decision=Decision.COACH,
            severity=Severity.MEDIUM,
            tier=Tier.TIER2_HIPAA if "hipaa" in logical_model else Tier.TIER2_COMPLIANCE,
            rationale="Judge graph terminated without a verdict.",
            coaching_message="Internal judge error; please retry.",
        )
    return verdict
