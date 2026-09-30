"""Tier-1 deterministic policy engine.

Runs synchronously on every gatekeeper request. Detects the 18 HIPAA Safe
Harbor identifiers (:mod:`axon.gatekeeper.phi`) and external-egress attempts,
redacts what's safely redactable, and escalates ambiguity to the Tier-2 LLM
judges.

The output is always a :class:`Verdict`. If the verdict's
``needs_escalation()`` returns True, the interceptor invokes Tier-2.
"""

from __future__ import annotations

import re
from typing import Any

from axon.gatekeeper import phi
from axon.gatekeeper.verdict import Decision, GatekeeperRequest, Severity, Tier, Verdict

# Internal/trusted domains; anything else in an outbound field is egress.
TRUSTED_DOMAINS = {"axonhealth.local", "axonhealth.internal"}

# Field names that, if they contain external addresses, indicate egress intent.
EGRESS_FIELDS = {"email_to", "recipient", "send_to", "to", "url", "webhook", "callback"}

# Verbs in the NATS subject that indicate platform-egress actions.
EGRESS_SUBJECT_VERBS = {"email", "send", "post", "publish_external", "webhook"}

def _is_external_address(value: str) -> bool:
    """True if value looks like an email/URL not pointing at a trusted domain."""
    m = re.search(r"@([\w.-]+)", value)
    if m:
        return m.group(1).lower() not in TRUSTED_DOMAINS
    m = re.search(r"https?://([^/\s]+)", value)
    if m:
        return m.group(1).lower() not in TRUSTED_DOMAINS
    return False


def _scan_egress(payload: dict[str, Any]) -> list[str]:
    """Return a list of matched-rule names if egress is detected."""
    matched: list[str] = []
    for key, value in payload.items():
        if not isinstance(value, str):
            continue
        if key.lower() in EGRESS_FIELDS and _is_external_address(value):
            matched.append(f"egress.{key.lower()}")
    return matched


def _redact_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return a copy of the payload with PHI redacted, plus matched rule names.

    A field whose name marks it as PHI (``patient_id``, ``dob``, ``address``)
    is replaced whole, at any depth. Every other string is scanned by
    :func:`phi.redact_text`. Raises :class:`phi.DetectorUnavailable`.
    """
    matched: list[str] = []

    def _scrub(value: Any) -> Any:
        if isinstance(value, str):
            out, findings = phi.redact_text(value)
            matched.extend(f"phi.{f.detector}.{f.kind}" for f in findings)
            return out
        if isinstance(value, dict):
            cleaned = {}
            for k, v in value.items():
                if phi.field_kind(str(k)) and v not in (None, ""):
                    cleaned[k] = "[REDACTED]"
                    matched.append(f"phi.field.{str(k).lower()}")
                else:
                    cleaned[k] = _scrub(v)
            return cleaned
        if isinstance(value, list):
            return [_scrub(v) for v in value]
        return value

    redacted = _scrub(payload)
    return redacted, list(dict.fromkeys(matched))


def evaluate(request: GatekeeperRequest) -> Verdict:
    """Run Tier-1 deterministic policy on the request and return a Verdict."""
    # Egress dominates everything — high-severity block.
    egress_hits = _scan_egress(request.payload)
    # Subjects are axon.{source}.{target}.{dept}.{verb}; an egress word in
    # either of the last two segments counts.
    for segment in request.subject.split(".")[-2:] if "." in request.subject else []:
        if segment in EGRESS_SUBJECT_VERBS:
            egress_hits.append(f"egress.subject.{segment}")

    if egress_hits:
        return Verdict(
            decision=Decision.BLOCK,
            severity=Severity.HIGH,
            tier=Tier.TIER1,
            rationale=(
                "External egress attempt detected by deterministic policy. "
                "Cross-platform PHI flow is not permitted without explicit BAA + HITL approval."
            ),
            matched_rules=egress_hits,
        )

    try:
        redacted_payload, phi_hits = _redact_payload(request.payload)
    except phi.DetectorUnavailable as exc:
        # Without the name detector a patient's name would pass unseen, so
        # nothing crosses. Same fail-safe as the judges.
        return Verdict(
            decision=Decision.COACH,
            severity=Severity.MEDIUM,
            tier=Tier.TIER1,
            rationale=str(exc),
            coaching_message="Gatekeeper PHI detector unavailable; please retry later.",
            matched_rules=["phi.detector_unavailable"],
        )
    if phi_hits:
        # PHI was redacted in transit. Escalate to Tier-2 for semantic check
        # in case the surrounding context still leaks (e.g., a free-text note
        # describes the patient by name even though the field is redacted).
        return Verdict(
            decision=Decision.REDACT,
            severity=Severity.LOW,
            tier=Tier.TIER1,
            rationale=(
                "PHI identifiers detected by deterministic policy. Redacted inflight; "
                "escalating to LLM judges for semantic context check."
            ),
            redacted_payload=redacted_payload,
            matched_rules=[*phi_hits, "escalate"],
        )

    # Cross-subsidiary boundary always escalates to Tier-2 even when clean.
    if request.target_subsidiary and request.target_subsidiary != request.source_subsidiary:
        return Verdict(
            decision=Decision.ALLOW,
            severity=Severity.LOW,
            tier=Tier.TIER1,
            rationale="Clean payload crossing subsidiary boundary; escalate to LLM judges.",
            matched_rules=["boundary.cross_subsidiary", "escalate"],
        )

    return Verdict(
        decision=Decision.ALLOW,
        severity=Severity.LOW,
        tier=Tier.TIER1,
        rationale="No PHI patterns or egress signals detected; intra-subsidiary message.",
    )
