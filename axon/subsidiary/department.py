"""Department contract shared by every subsidiary.

A department is a LangGraph workflow with its own logical model. It receives a
task dict and returns a result dict. It never touches the bus: when it needs
another subsidiary, it calls the ``consult`` function its Supervisor hands it,
and the Supervisor's runtime is the one that publishes through the gatekeeper.
Keeping NATS out of this module (and out of every department module) is what
makes "one well-known publisher per subsidiary" true in code, not just in docs.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from axon.model_registry import get_client

# (target_subsidiary, target_department, payload) -> the target's reply payload.
Consult = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


class ConsultationError(Exception):
    """A consultation that did not produce a reply.

    ``decision`` is the gatekeeper decision that stopped it (``coach`` or
    ``block``), or ``timeout`` when no reply arrived in time.
    """

    def __init__(
        self,
        decision: str,
        reason: str,
        *,
        coaching_message: str | None = None,
        incident_id: str | None = None,
    ) -> None:
        super().__init__(f"{decision}: {reason}")
        self.decision = decision
        self.reason = reason
        self.coaching_message = coaching_message
        self.incident_id = incident_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "coaching_message": self.coaching_message,
            "incident_id": self.incident_id,
        }


class Department(Protocol):
    name: str
    description: str

    async def handle(self, task: dict[str, Any], consult: Consult) -> dict[str, Any]: ...


async def ask_model(
    logical_model: str, user_message: str, *, extra_context: str | None = None
) -> str:
    """Call a department's logical model without blocking the event loop."""
    client = get_client(logical_model)
    return await asyncio.to_thread(client.chat, user_message, extra_context=extra_context)


_BRACE_JSON = re.compile(r"\{[\s\S]*\}")


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of model output, or None."""
    match = _BRACE_JSON.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
