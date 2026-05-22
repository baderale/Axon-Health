"""Compliance Agent — the Tier-2 LLM judge for everything HIPAA doesn't cover.

Thin binding over :mod:`axon.gatekeeper.judge` with the
``compliance-judge.v0`` logical model.
"""

from __future__ import annotations

from axon.gatekeeper.judge import judge
from axon.gatekeeper.verdict import GatekeeperRequest, Verdict

LOGICAL_MODEL = "compliance-judge.v0"


async def evaluate(request: GatekeeperRequest) -> Verdict:
    return await judge(LOGICAL_MODEL, request)
