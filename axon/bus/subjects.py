"""Canonical NATS subject names for the Axon Health platform.

All cross-subsidiary traffic, gatekeeper traffic, audit, and incident flows
use subjects under the ``axon.*`` root. Centralizing the strings here keeps
the bus contract auditable.
"""

from __future__ import annotations


class Subjects:
    """Top-level subject roots."""

    # Inbound to the gatekeeper pipeline. Anything a Supervisor wants to
    # publish cross-subsidiary lands here first.
    GATEKEEPER_IN = "axon.gatekeeper.in"

    # Outbound after gatekeeper approval. Each target subsidiary subscribes to
    # its own inbox under this root (see ``inbox``); the interceptor picks the
    # inbox from ``target_subsidiary``, never from anything the sender supplies.
    GATEKEEPER_OUT = "axon.gatekeeper.out"

    # Operator / user input into one subsidiary (request-reply). Not
    # cross-subsidiary traffic, so it does not pass the gatekeeper.
    INGRESS_PREFIX = "axon.ingress"

    # Verdict announcements (informational; the source subsidiary listens for
    # coach/block verdicts that affect its own run).
    GATEKEEPER_VERDICT = "axon.gatekeeper.verdict"

    # JetStream-backed audit log. Every gatekeeper event is mirrored here.
    AUDIT_PREFIX = "AUDIT"
    AUDIT_ALL = "AUDIT.>"

    # JetStream-backed incident queue. Blocks open an incident here.
    INCIDENT_PREFIX = "INCIDENT"
    INCIDENT_ALL = "INCIDENT.>"

    # HITL resolution events (incident_id -> approve|deny).
    HITL_VERDICT = "axon.hitl.verdict"

    @staticmethod
    def cross_subsidiary(source: str, target: str, dept: str, verb: str) -> str:
        return f"axon.{source}.{target}.{dept}.{verb}"

    @staticmethod
    def parse_cross_subsidiary(subject: str) -> tuple[str, str, str, str] | None:
        """Inverse of :meth:`cross_subsidiary`: (source, target, dept, verb)."""
        parts = subject.split(".")
        if len(parts) != 5 or parts[0] != "axon":
            return None
        return parts[1], parts[2], parts[3], parts[4]

    @staticmethod
    def inbox(subsidiary: str) -> str:
        return f"{Subjects.GATEKEEPER_OUT}.{subsidiary}"

    @staticmethod
    def ingress(subsidiary: str) -> str:
        return f"{Subjects.INGRESS_PREFIX}.{subsidiary}"

    @staticmethod
    def audit(trace_id: str) -> str:
        return f"{Subjects.AUDIT_PREFIX}.{trace_id}"

    @staticmethod
    def incident(incident_id: str) -> str:
        return f"{Subjects.INCIDENT_PREFIX}.{incident_id}"
