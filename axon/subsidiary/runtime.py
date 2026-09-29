"""Subsidiary runtime: the only code in a subsidiary that talks to the bus.

One runtime per subsidiary. It:

  - accepts operator tasks on ``axon.ingress.<name>`` (request-reply) and runs
    them through the Supervisor;
  - gives departments a ``consult`` function that publishes a
    ``GatekeeperRequest`` on ``axon.gatekeeper.in`` and waits for the reply;
  - receives gatekeeper-cleared messages on its inbox
    ``axon.gatekeeper.out.<name>``: replies resolve a waiting consult, requests
    run the named department and are answered back through the gatekeeper;
  - watches ``axon.gatekeeper.verdict`` so a coach or block on one of its own
    messages (or on the reply to one) fails the waiting consult immediately
    instead of letting it hang until the timeout.
"""

from __future__ import annotations

import asyncio
import os
import signal
import uuid
from typing import Any

import structlog
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg

from axon.bus.nats_client import decode_json, publish_json, session, subscribe
from axon.bus.subjects import Subjects
from axon.gatekeeper.verdict import GatekeeperRequest
from axon.subsidiary.department import Consult, ConsultationError
from axon.subsidiary.supervisor import Supervisor

log = structlog.get_logger(__name__)

_STOPPING_DECISIONS = {"coach", "block"}


def _consult_timeout() -> float:
    # Every consult crosses the gatekeeper twice (two LLM judges each way) plus
    # the target department's own model call. On CPU-only Ollama that is slow.
    return float(os.environ.get("AXON_CONSULT_TIMEOUT", "300"))


class SubsidiaryRuntime:
    def __init__(self, supervisor: Supervisor, *, consult_timeout: float | None = None) -> None:
        self.supervisor = supervisor
        self.name = supervisor.name
        self.consult_timeout = consult_timeout or _consult_timeout()
        self._nc: NATS | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    # ---- wiring ---------------------------------------------------------

    async def attach(self, nc: NATS) -> None:
        """Subscribe this subsidiary on an open NATS connection."""
        self._nc = nc
        await subscribe(nc, Subjects.inbox(self.name), self._on_inbox)
        await subscribe(nc, Subjects.GATEKEEPER_VERDICT, self._on_verdict)
        await subscribe(nc, Subjects.ingress(self.name), self._on_ingress)
        log.info("subsidiary.started", subsidiary=self.name)

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # ---- outbound -------------------------------------------------------

    def consult_for(self, conversation_id: str) -> Consult:
        async def consult(target: str, dept: str, payload: dict[str, Any]) -> dict[str, Any]:
            request = GatekeeperRequest(
                source_subsidiary=self.name,
                target_subsidiary=target,
                subject=Subjects.cross_subsidiary(self.name, target, dept, "query"),
                payload=payload,
                headers={"conversation_id": conversation_id},
            )
            future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
            self._pending[request.trace_id] = future
            try:
                await self._publish_to_gatekeeper(request)
                return await asyncio.wait_for(future, timeout=self.consult_timeout)
            except TimeoutError as exc:
                raise ConsultationError(
                    "timeout", f"No reply from {target}.{dept} in {self.consult_timeout:.0f}s"
                ) from exc
            finally:
                self._pending.pop(request.trace_id, None)

        return consult

    async def _publish_to_gatekeeper(self, request: GatekeeperRequest) -> None:
        assert self._nc is not None, "runtime is not attached"
        log.info(
            "subsidiary.publish",
            subsidiary=self.name,
            subject=request.subject,
            trace_id=request.trace_id,
        )
        await publish_json(self._nc, Subjects.GATEKEEPER_IN, request.model_dump(mode="json"))

    # ---- inbound --------------------------------------------------------

    async def _on_ingress(self, msg: Msg) -> None:
        self._spawn(self._handle_ingress(msg))

    async def _handle_ingress(self, msg: Msg) -> None:
        conversation_id = str(uuid.uuid4())
        try:
            task = decode_json(msg)
            result = await self.supervisor.run(task, self.consult_for(conversation_id))
        except Exception as exc:  # noqa: BLE001
            log.exception("subsidiary.ingress_failed", subsidiary=self.name, error=str(exc))
            result = {"error": f"{type(exc).__name__}: {exc}"}
        if msg.reply:
            await publish_json(
                self._nc, msg.reply, {"conversation_id": conversation_id, "result": result}
            )

    async def _on_inbox(self, msg: Msg) -> None:
        envelope = decode_json(msg)
        in_reply_to = envelope.get("in_reply_to")
        if in_reply_to:
            future = self._pending.get(in_reply_to)
            if future and not future.done():
                future.set_result(envelope.get("payload") or {})
            return
        self._spawn(self._answer_request(envelope))

    async def _answer_request(self, envelope: dict[str, Any]) -> None:
        parsed = Subjects.parse_cross_subsidiary(envelope.get("original_subject", ""))
        if parsed is None:
            log.warning("subsidiary.bad_subject", subsidiary=self.name, envelope=envelope)
            return
        source, _target, dept, _verb = parsed
        payload = envelope.get("payload") or {}
        conversation_id = envelope.get("conversation_id") or str(uuid.uuid4())
        try:
            result = await self.supervisor.run(
                {**payload, "department": dept}, self.consult_for(conversation_id)
            )
            # Reply with what the department produced, not an echo of the request.
            reply = {k: v for k, v in result.items() if k not in payload}
        except Exception as exc:  # noqa: BLE001
            log.exception("subsidiary.request_failed", subsidiary=self.name, error=str(exc))
            reply = {"error": f"{type(exc).__name__}: {exc}"}

        await self._publish_to_gatekeeper(
            GatekeeperRequest(
                source_subsidiary=self.name,
                target_subsidiary=source,
                subject=Subjects.cross_subsidiary(self.name, source, dept, "reply"),
                payload=reply,
                headers={
                    "in_reply_to": envelope["trace_id"],
                    "conversation_id": conversation_id,
                },
            )
        )

    async def _on_verdict(self, msg: Msg) -> None:
        envelope = decode_json(msg)
        verdict = envelope.get("verdict") or {}
        if verdict.get("decision") not in _STOPPING_DECISIONS:
            return
        # Our own outbound request was stopped, or the reply to it was.
        key = envelope.get("trace_id")
        if key not in self._pending:
            key = envelope.get("in_reply_to")
        future = self._pending.get(key) if key else None
        if future is None or future.done():
            return
        future.set_exception(
            ConsultationError(
                verdict["decision"],
                verdict.get("rationale", ""),
                coaching_message=verdict.get("coaching_message"),
                incident_id=verdict.get("incident_id"),
            )
        )

    # ---- service entry point -------------------------------------------

    async def run_forever(self) -> None:
        async with session() as (nc, _js):
            await self.attach(nc)
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop.set)
                except NotImplementedError:
                    pass  # Windows
            await stop.wait()
