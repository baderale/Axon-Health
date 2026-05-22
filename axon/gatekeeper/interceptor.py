"""Gatekeeper interceptor service.

Subscribes to ``axon.gatekeeper.in``. For every cross-subsidiary message:

  1. Run Tier-1 deterministic policy.
  2. Mirror the result to AUDIT.*.
  3. If Tier-1 BLOCKs                 -> open INCIDENT, publish verdict, stop.
  4. If Tier-1 REDACTs / ALLOWs+escalate -> run HIPAA Agent (Tier-2).
  5. If HIPAA passes (allow/redact)     -> run Compliance Agent (Tier-2).
  6. Combine the verdicts into a final outcome:
        - any BLOCK   -> open INCIDENT, publish verdict, stop.
        - any COACH   -> publish verdict, stop.
        - any REDACT  -> publish redacted payload on axon.gatekeeper.out.
        - all ALLOW   -> publish original payload on axon.gatekeeper.out.
  7. Always emit a final AUDIT entry for what was published.

Each step is idempotent on the trace_id so re-deliveries don't double-publish.
"""

from __future__ import annotations

import asyncio
import os
import signal

import structlog
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js.client import JetStreamContext

from axon.audit.streams import emit_audit, open_incident
from axon.bus.nats_client import (
    decode_json,
    ensure_streams,
    publish_json,
    session,
    subscribe,
)
from axon.bus.subjects import Subjects
from axon.gatekeeper import compliance_agent, hipaa_agent, tier1_policy
from axon.gatekeeper.verdict import (
    Decision,
    GatekeeperRequest,
    Severity,
    Tier,
    Verdict,
)

log = structlog.get_logger(__name__)


def _combine_for_redact(
    request: GatekeeperRequest,
    tier1: Verdict,
    tier2_verdicts: list[Verdict],
) -> tuple[Verdict, dict]:
    """Resolve the final decision across Tier-1 + Tier-2 verdicts.

    Returns (final_verdict, final_payload). final_payload is whatever should
    be republished on axon.gatekeeper.out when the decision is allow or redact.
    """
    all_verdicts = [tier1, *tier2_verdicts]

    # BLOCK dominates.
    blockers = [v for v in all_verdicts if v.decision is Decision.BLOCK]
    if blockers:
        worst = max(
            blockers,
            key=lambda v: ("low", "medium", "high").index(v.severity.value),
        )
        return worst, request.payload

    # Then COACH.
    coaches = [v for v in all_verdicts if v.decision is Decision.COACH]
    if coaches:
        return coaches[0], request.payload

    # REDACT — start from the last redacted_payload available, else original.
    payload = request.payload
    matched = list(tier1.matched_rules)
    redacted_any = False
    for v in all_verdicts:
        if v.decision is Decision.REDACT and v.redacted_payload is not None:
            payload = v.redacted_payload
            redacted_any = True
            matched.extend(v.matched_rules)

    if redacted_any:
        return (
            Verdict(
                decision=Decision.REDACT,
                severity=Severity.LOW,
                tier=Tier.TIER2_COMPLIANCE if tier2_verdicts else Tier.TIER1,
                rationale="Payload redacted by gatekeeper pipeline.",
                redacted_payload=payload,
                matched_rules=matched,
            ),
            payload,
        )

    return (
        Verdict(
            decision=Decision.ALLOW,
            severity=Severity.LOW,
            tier=Tier.TIER2_COMPLIANCE if tier2_verdicts else Tier.TIER1,
            rationale="Payload cleared by gatekeeper pipeline.",
            matched_rules=matched,
        ),
        payload,
    )


async def handle_request(
    nc: NATS,
    js: JetStreamContext,
    request: GatekeeperRequest,
) -> None:
    """Single end-to-end run of the gatekeeper pipeline for one request."""
    log.info(
        "gatekeeper.received",
        trace_id=request.trace_id,
        subject=request.subject,
        source=request.source_subsidiary,
        target=request.target_subsidiary,
    )

    # Tier 1.
    tier1 = tier1_policy.evaluate(request)
    await emit_audit(js, stage=f"tier1.{tier1.decision.value}", request=request, verdict=tier1)

    # Tier-1 BLOCK is terminal.
    if tier1.decision is Decision.BLOCK:
        await _finalize_block(nc, js, request, tier1)
        return

    # Tier-2 only when the boundary is being crossed or Tier-1 escalates.
    tier2_verdicts: list[Verdict] = []
    if tier1.needs_escalation() or tier1.decision is Decision.REDACT:
        hipaa_v = await hipaa_agent.evaluate(request)
        await emit_audit(
            js, stage=f"tier2.hipaa.{hipaa_v.decision.value}", request=request, verdict=hipaa_v
        )
        tier2_verdicts.append(hipaa_v)
        if hipaa_v.decision is not Decision.BLOCK:
            comp_v = await compliance_agent.evaluate(request)
            await emit_audit(
                js,
                stage=f"tier2.compliance.{comp_v.decision.value}",
                request=request,
                verdict=comp_v,
            )
            tier2_verdicts.append(comp_v)

    final_verdict, final_payload = _combine_for_redact(request, tier1, tier2_verdicts)

    # Always announce the verdict on the verdict subject.
    await publish_json(nc, Subjects.GATEKEEPER_VERDICT, final_verdict.model_dump(mode="json"))

    if final_verdict.decision is Decision.BLOCK:
        await _finalize_block(nc, js, request, final_verdict)
        return

    if final_verdict.decision is Decision.COACH:
        await emit_audit(
            js, stage="interceptor.coached", request=request, verdict=final_verdict
        )
        return

    # ALLOW or REDACT: republish payload on the outbound channel.
    out_subject = request.headers.get("forward_to", Subjects.GATEKEEPER_OUT)
    envelope = {
        "trace_id": request.trace_id,
        "source_subsidiary": request.source_subsidiary,
        "target_subsidiary": request.target_subsidiary,
        "original_subject": request.subject,
        "payload": final_payload,
        "redacted": final_verdict.decision is Decision.REDACT,
    }
    await publish_json(nc, out_subject, envelope)
    await emit_audit(
        js,
        stage=f"interceptor.published.{final_verdict.decision.value}",
        request=request,
        verdict=final_verdict,
        final_payload=final_payload,
    )


async def _finalize_block(
    nc: NATS, js: JetStreamContext, request: GatekeeperRequest, verdict: Verdict
) -> None:
    incident = await open_incident(js, request=request, verdict=verdict)
    blocked = verdict.model_copy(update={"incident_id": incident.incident_id})
    await publish_json(nc, Subjects.GATEKEEPER_VERDICT, blocked.model_dump(mode="json"))
    await emit_audit(js, stage="interceptor.blocked", request=request, verdict=blocked)


async def _decode_request(msg: Msg) -> GatekeeperRequest | None:
    try:
        data = decode_json(msg)
        return GatekeeperRequest.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        log.warning("interceptor.decode_failed", error=str(exc), raw=msg.data[:200])
        return None


async def run() -> None:
    """Start the interceptor service. Blocks until cancelled."""
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), os.environ.get("LOG_LEVEL", "INFO"))
        )
    )
    async with session() as (nc, js):
        await ensure_streams(js)
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass  # Windows

        async def handler(msg: Msg) -> None:
            request = await _decode_request(msg)
            if request is None:
                return
            try:
                await handle_request(nc, js, request)
            except Exception as exc:  # noqa: BLE001
                log.exception("interceptor.unhandled_error", error=str(exc))

        await subscribe(nc, Subjects.GATEKEEPER_IN, handler, queue="gatekeeper-interceptor")
        log.info("interceptor.started", subject=Subjects.GATEKEEPER_IN)
        await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(run())
