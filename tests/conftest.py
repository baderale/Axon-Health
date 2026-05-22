"""Pytest fixtures and skip-logic for the gatekeeper test suite.

Tests fall into two tiers:

  - Unit tests (``test_tier1_policy.py``) require no infrastructure and run
    on any machine with the package installed.
  - Integration tests (``test_interceptor.py``) require a running NATS
    JetStream broker. They are auto-skipped if NATS is not reachable on
    ``$NATS_URL`` (or the default ``nats://localhost:4222``).
"""

from __future__ import annotations

import asyncio
import os

import pytest


@pytest.fixture(scope="session")
def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


def _nats_reachable(url: str) -> bool:
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 4222
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=False)
def require_nats(nats_url: str) -> None:
    if not _nats_reachable(nats_url):
        pytest.skip(
            f"NATS not reachable at {nats_url}. "
            "Run `docker compose up -d nats` to enable integration tests."
        )
