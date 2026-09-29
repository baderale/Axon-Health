"""Build the Enterprise Console page from a data snapshot.

    python -m axon.tools.dashboard             # rebuild the page from snapshot.json
    python -m axon.tools.dashboard --refresh   # re-read AUDIT from NATS first

The page is ``docs/dashboard/axon-console.html``, made from
``docs/dashboard/console.template.html`` plus ``docs/dashboard/snapshot.json``.
See ``docs/dashboard/README.md`` for how it is published and shared.

``--refresh`` keeps every conversation whose judges were real models and drops
the ones produced by the automated tests (their stub judges' rationales start
with "stub "). Hand-written notes and final answers already in the snapshot
are kept; add them for new runs by editing ``snapshot.json``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "docs" / "dashboard"
TEMPLATE = DASHBOARD_DIR / "console.template.html"
SNAPSHOT = DASHBOARD_DIR / "snapshot.json"
OUTPUT = DASHBOARD_DIR / "axon-console.html"

_EVENT_FIELDS = ("conv", "stage", "subject", "src", "tgt", "at", "rationale", "coaching", "sent", "forwarded")


async def _read_audit() -> tuple[int, list[dict]]:
    from nats.errors import TimeoutError as NatsTimeoutError

    from axon.bus.nats_client import session
    from axon.bus.subjects import Subjects

    events: list[dict] = []
    total = 0
    async with session() as (_nc, js):
        sub = await js.subscribe(Subjects.AUDIT_ALL, ordered_consumer=True)
        while True:
            try:
                msg = await sub.next_msg(timeout=2)
            except NatsTimeoutError:
                break
            total += 1
            event = json.loads(msg.data)
            request = event["request"]
            conversation = request["headers"].get("conversation_id")
            if not conversation:
                continue  # gatekeeper-only traffic (fake_publisher, interceptor tests)
            verdict = event.get("verdict") or {}
            events.append(
                {
                    "conv": conversation,
                    "stage": event["stage"],
                    "subject": request["subject"],
                    "src": request["source_subsidiary"],
                    "tgt": request["target_subsidiary"],
                    "at": event["recorded_at"],
                    "rationale": verdict.get("rationale"),
                    "coaching": verdict.get("coaching_message"),
                    "sent": request["payload"],
                    "forwarded": event.get("final_payload"),
                }
            )
    stubbed = {e["conv"] for e in events if (e["rationale"] or "").startswith("stub ")}
    return total, [e for e in events if e["conv"] not in stubbed]


def _revision() -> str:
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
        return f"branch {branch} · {commit}"
    except (OSError, subprocess.CalledProcessError):
        return ""


def refresh() -> dict:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    total, events = asyncio.run(_read_audit())
    runs = snapshot.get("runs", {})
    for conv in sorted({e["conv"] for e in events}):
        runs.setdefault(conv, {"note": "", "final_answer": ""})
    snapshot.update(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        revision=_revision(),
        total_audit_events=total,
        runs=runs,
        events=[{k: e[k] for k in _EVENT_FIELDS} for e in events],
    )
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, default=str) + "\n", encoding="utf-8")
    return snapshot


def build() -> Path:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    data = json.dumps(snapshot, default=str).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*SNAPSHOT*/null", data, 1)
    OUTPUT.write_text(html, encoding="utf-8")
    return OUTPUT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Re-read AUDIT from NATS first")
    args = parser.parse_args(argv)
    if args.refresh:
        snapshot = refresh()
        print(f"snapshot: {len(snapshot['events'])} live-run events of {snapshot['total_audit_events']}")
    print(f"built {build()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
