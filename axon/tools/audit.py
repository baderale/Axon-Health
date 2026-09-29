"""Print the AUDIT trail, optionally for one conversation.

Examples:
    python -m axon.tools.audit                      # everything, oldest first
    python -m axon.tools.audit <conversation_id>    # one question, both legs

``conversation_id`` is what ``axon.tools.ask`` prints.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from nats.errors import TimeoutError as NatsTimeoutError

from axon.bus.nats_client import session
from axon.bus.subjects import Subjects


async def _run(conversation_id: str | None, show_payloads: bool) -> int:
    async with session() as (_nc, js):
        sub = await js.subscribe(Subjects.AUDIT_ALL, ordered_consumer=True)
        shown = 0
        while True:
            try:
                msg = await sub.next_msg(timeout=2)
            except NatsTimeoutError:
                break
            event = json.loads(msg.data)
            request = event["request"]
            if conversation_id and request["headers"].get("conversation_id") != conversation_id:
                continue
            shown += 1
            verdict = event.get("verdict") or {}
            print(f"{event['stage']:<32} {request['subject']:<48} {verdict.get('rationale', '')}")
            if show_payloads and event.get("final_payload") is not None:
                print(f"    forwarded: {json.dumps(event['final_payload'], default=str)}")
    if not shown:
        print("(no matching audit events)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("conversation_id", nargs="?")
    parser.add_argument("--payloads", action="store_true", help="Show forwarded payloads")
    args = parser.parse_args(argv)
    return asyncio.run(_run(args.conversation_id, args.payloads))


if __name__ == "__main__":
    raise SystemExit(main())
