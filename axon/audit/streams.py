"""Helpers for the AUDIT.* and INCIDENT.* JetStream streams.

Every gatekeeper event ends up in AUDIT. Every BLOCK verdict opens an
INCIDENT for human-in-the-loop review. HITL approve/deny resolves it.
"""

from __future__ import annotations

from typing import Any

from nats.js.client import JetStreamContext

from axon.bus.nats_client import publish_jetstream
from axon.bus.subjects import Subjects
from axon.gatekeeper.verdict import (
    AuditEvent,
    GatekeeperRequest,
    Incident,
    Severity,
    Verdict,
)


async def emit_audit(
    js: JetStreamContext,
    *,
    stage: str,
    request: GatekeeperRequest,
    verdict: Verdict | None = None,
    final_payload: dict[str, Any] | None = None,
) -> None:
    """Append one AUDIT.<trace_id> event."""
    event = AuditEvent(
        trace_id=request.trace_id,
        stage=stage,
        request=request,
        verdict=verdict,
        final_payload=final_payload,
    )
    await publish_jetstream(
        js,
        Subjects.audit(request.trace_id),
        event.model_dump(mode="json"),
    )


async def open_incident(
    js: JetStreamContext,
    *,
    request: GatekeeperRequest,
    verdict: Verdict,
) -> Incident:
    """Open an INCIDENT.<incident_id> for a BLOCK verdict."""
    incident = Incident(
        trace_id=request.trace_id,
        severity=verdict.severity or Severity.HIGH,
        request=request,
        verdict=verdict,
    )
    await publish_jetstream(
        js,
        Subjects.incident(incident.incident_id),
        incident.model_dump(mode="json"),
    )
    return incident


async def resolve_incident(
    js: JetStreamContext,
    *,
    incident: Incident,
    status: str,
    resolver: str,
) -> None:
    """Append a resolution event for an incident. ``status`` is approved|denied."""
    if status not in ("approved", "denied"):
        raise ValueError(f"Invalid incident status: {status!r}")
    incident = incident.model_copy(update={"status": status, "resolver": resolver})
    await publish_jetstream(
        js,
        f"{Subjects.incident(incident.incident_id)}.resolved",
        incident.model_dump(mode="json"),
    )
