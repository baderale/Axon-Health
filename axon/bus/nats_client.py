"""Thin async wrappers around nats-py for the Axon Health platform.

Two responsibilities:
  - Connect once per process; expose typed publish/subscribe helpers.
  - Ensure JetStream is bootstrapped with the AUDIT and INCIDENT streams the
    audit module requires.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js.api import RetentionPolicy, StorageType, StreamConfig
from nats.js.client import JetStreamContext

from axon.bus.subjects import Subjects


def _nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://nats:4222")


async def connect() -> tuple[NATS, JetStreamContext]:
    """Connect to NATS and return the connection plus JetStream context."""
    nc = await nats.connect(_nats_url(), connect_timeout=10)
    js = nc.jetstream()
    return nc, js


@asynccontextmanager
async def session() -> AsyncIterator[tuple[NATS, JetStreamContext]]:
    """Connect, yield, and close on exit."""
    nc, js = await connect()
    try:
        yield nc, js
    finally:
        await nc.drain()


async def ensure_streams(js: JetStreamContext) -> None:
    """Create AUDIT.* and INCIDENT.* streams if they don't already exist."""
    await _upsert_stream(
        js,
        StreamConfig(
            name=Subjects.AUDIT_PREFIX,
            subjects=[Subjects.AUDIT_ALL],
            retention=RetentionPolicy.LIMITS,
            storage=StorageType.FILE,
            max_age=7 * 365 * 24 * 3600,  # 7 years, HIPAA minimum
        ),
    )
    await _upsert_stream(
        js,
        StreamConfig(
            name=Subjects.INCIDENT_PREFIX,
            subjects=[Subjects.INCIDENT_ALL],
            retention=RetentionPolicy.LIMITS,
            storage=StorageType.FILE,
        ),
    )


async def _upsert_stream(js: JetStreamContext, cfg: StreamConfig) -> None:
    try:
        await js.add_stream(config=cfg)
    except Exception:  # noqa: BLE001 - nats-py raises generic on duplicate; update is fine
        try:
            await js.update_stream(config=cfg)
        except Exception:
            pass


async def publish_json(nc: NATS, subject: str, payload: dict[str, Any]) -> None:
    """Publish a JSON-serialized dict on a core NATS subject."""
    await nc.publish(subject, json.dumps(payload, default=str).encode("utf-8"))


async def publish_jetstream(js: JetStreamContext, subject: str, payload: dict[str, Any]) -> None:
    """Publish a JSON-serialized dict on a JetStream-backed subject."""
    await js.publish(subject, json.dumps(payload, default=str).encode("utf-8"))


def decode_json(msg: Msg) -> dict[str, Any]:
    return json.loads(msg.data.decode("utf-8"))


Handler = Callable[[Msg], Awaitable[None]]


async def subscribe(nc: NATS, subject: str, handler: Handler, *, queue: str | None = None):
    """Convenience wrapper that returns a subscription."""
    return await nc.subscribe(subject, cb=handler, queue=queue)
