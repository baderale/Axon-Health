"""Send a clinical case to a subsidiary and print its answer.

Examples:
    python -m axon.tools.ask "Patient_id 12345, MRN MRN-AX-99182, hepatic impairment. \
Safe dosing window for acetaminophen?"
    python -m axon.tools.ask --subsidiary pharma --department research "Max daily ibuprofen?"

The case goes to ``axon.ingress.<subsidiary>``. Anything that subsidiary
sends to another one passes through the gatekeeper; follow it in the AUDIT
stream by the conversation id printed here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from axon.bus.nats_client import session
from axon.bus.subjects import Subjects


async def _run(subsidiary: str, case: str, department: str | None, timeout: float) -> int:
    task: dict[str, str] = {"case": case}
    if department:
        task = {"department": department, "question": case}
    async with session() as (nc, _js):
        try:
            msg = await nc.request(
                Subjects.ingress(subsidiary), json.dumps(task).encode("utf-8"), timeout=timeout
            )
        except Exception as exc:  # noqa: BLE001 - nats raises NoResponders / Timeout
            print(f"No answer from {subsidiary}: {type(exc).__name__} {exc}", file=sys.stderr)
            return 1
    body = json.loads(msg.data)
    print(f"conversation_id: {body.get('conversation_id')}")
    print(json.dumps(body.get("result"), indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", help="Free-text case or question")
    parser.add_argument("--subsidiary", default="clinical_research")
    parser.add_argument("--department", help="Send straight to one department")
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args(argv)
    return asyncio.run(_run(args.subsidiary, args.case, args.department, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
