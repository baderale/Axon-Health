"""Tier-1 deterministic policy engine.

Runs synchronously on every gatekeeper request. Sub-millisecond. Detects
known PHI patterns and external-egress attempts, redacts what's safely
redactable, and escalates ambiguity to the Tier-2 LLM judges.

The output is always a :class:`Verdict`. If the verdict's
``needs_escalation()`` returns True, the interceptor invokes Tier-2.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from axon.gatekeeper.verdict import Decision, GatekeeperRequest, Severity, Tier, Verdict

# Internal/trusted domains; anything else in an outbound field is egress.
TRUSTED_DOMAINS = {"axonhealth.local", "axonhealth.internal"}

# Field names that, if they contain external addresses, indicate egress intent.
EGRESS_FIELDS = {"email_to", "recipient", "send_to", "to", "url", "webhook", "callback"}

# Verbs in the NATS subject that indicate platform-egress actions.
EGRESS_SUBJECT_VERBS = {"email", "send", "post", "publish_external", "webhook"}

_PHI_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("patient_id", re.compile(r"(?i)\bpatient[\s_-]?id\b\s*[:#=]?\s*(\d{3,})")),
    ("mrn", re.compile(r"(?i)\bMRN\b\s*[:#=]?\s*([A-Z0-9-]{4,})")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("dob", re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")),
    ("phone", re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]

_PHI_FIELD_NAMES = {"patient_id", "mrn", "ssn", "dob", "date_of_birth"}


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
    """Return a deep-copied payload with PHI redacted, plus matched rule names."""
    redacted = deepcopy(payload)
    matched: list[str] = []

    for key in list(redacted.keys()):
        if key.lower() in _PHI_FIELD_NAMES and redacted[key] is not None:
            redacted[key] = "[REDACTED]"
            matched.append(f"phi.field.{key.lower()}")

    def _scrub(value: Any) -> Any:
        if isinstance(value, str):
            out = value
            for name, pattern in _PHI_PATTERNS:
                if pattern.search(out):
                    out = pattern.sub(f"[REDACTED:{name}]", out)
                    matched.append(f"phi.pattern.{name}")
            return out
        if isinstance(value, dict):
            return {k: _scrub(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_scrub(v) for v in value]
        return value

    redacted = {k: _scrub(v) for k, v in redacted.items()}
    return redacted, matched


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

    redacted_payload, phi_hits = _redact_payload(request.payload)
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
