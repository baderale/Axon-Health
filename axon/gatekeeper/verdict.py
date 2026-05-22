"""Severity-ladder verdict schema for the gatekeepers.

The verdict is the single contract between any policy/judge that inspects a
cross-subsidiary message and the interceptor that decides what to do next.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Decision(str, Enum):
    ALLOW = "allow"
    REDACT = "redact"
    COACH = "coach"
    BLOCK = "block"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Tier(str, Enum):
    TIER1 = "tier1"  # deterministic policy
    TIER2_HIPAA = "tier2_hipaa"
    TIER2_COMPLIANCE = "tier2_compliance"


class GatekeeperRequest(BaseModel):
    """Envelope for any message the interceptor evaluates."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_subsidiary: str
    target_subsidiary: str | None = None
    subject: str
    payload: dict[str, Any]
    headers: dict[str, str] = Field(default_factory=dict)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Verdict(BaseModel):
    """The single contract returned by Tier-1 policy and Tier-2 LLM judges."""

    decision: Decision
    severity: Severity = Severity.LOW
    tier: Tier
    rationale: str
    redacted_payload: dict[str, Any] | None = None
    coaching_message: str | None = None
    incident_id: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_terminal(self) -> bool:
        """True if this verdict ends the gatekeeper pipeline."""
        return self.decision in (Decision.BLOCK, Decision.COACH)

    def needs_escalation(self) -> bool:
        """True if Tier-1 wants Tier-2 LLM judges to weigh in."""
        return self.decision == Decision.ALLOW and "escalate" in self.matched_rules


class AuditEvent(BaseModel):
    """One row in the AUDIT.* stream."""

    trace_id: str
    stage: str  # e.g. "tier1.allow", "tier2.hipaa.redact", "interceptor.published"
    request: GatekeeperRequest
    verdict: Verdict | None = None
    final_payload: dict[str, Any] | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Incident(BaseModel):
    """One row in the INCIDENT.* stream — opened on BLOCK verdicts."""

    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    severity: Severity
    request: GatekeeperRequest
    verdict: Verdict
    status: str = "open"  # open | approved | denied
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    resolver: str | None = None
