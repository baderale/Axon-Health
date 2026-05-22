"""CLI tool that drives the gatekeeper layer with synthetic traffic.

Examples:
    python -m axon.tools.fake_publisher allow
    python -m axon.tools.fake_publisher redact
    python -m axon.tools.fake_publisher block
    python -m axon.tools.fake_publisher intra

Each invocation publishes one synthetic GatekeeperRequest on
``axon.gatekeeper.in`` and prints any verdict / forwarded payload received
within a short timeout.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from nats.aio.msg import Msg

from axon.bus.nats_client import decode_json, publish_json, session, subscribe
from axon.bus.subjects import Subjects
from axon.gatekeeper.verdict import GatekeeperRequest


SCENARIOS: dict[str, GatekeeperRequest] = {
    "allow": GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.research.query",
        payload={
            "question": (
                "What is the standard adult dose of acetaminophen for moderate pain?"
            ),
            "category": "drug_information",
        },
    ),
    "redact": GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.research.query",
        payload={
            "patient_id": "12345",
            "mrn": "MRN-AX-99182",
            "condition": "hepatic impairment",
            "drug": "acetaminophen",
            "question": (
                "For patient_id 12345 (MRN MRN-AX-99182) presenting with hepatic "
                "impairment, what is the safe dosing window for acetaminophen?"
            ),
        },
    ),
    "block": GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="pharma",
        subject="axon.clinical_research.pharma.email.send",
        payload={
            "email_to": "outside-collaborator@gmail.com",
            "subject": "Patient #12345 record",
            "body": (
                "Please find attached the full clinical record for patient_id 12345, "
                "MRN MRN-AX-99182, including DOB 1972-04-15."
            ),
        },
    ),
    "intra": GatekeeperRequest(
        source_subsidiary="clinical_research",
        target_subsidiary="clinical_research",
        subject="axon.clinical_research.clinical_research.compliance_dept.check",
        payload={"question": "Does this documentation meet our internal SOP?"},
    ),
}


async def _run(scenario: str, *, timeout: float) -> int:
    if scenario not in SCENARIOS:
        print(f"Unknown scenario {scenario!r}. Known: {sorted(SCENARIOS)}", file=sys.stderr)
        return 2

    request = SCENARIOS[scenario]
    received: list[tuple[str, dict]] = []
    done = asyncio.Event()

    async with session() as (nc, _js):

        async def on_verdict(msg: Msg) -> None:
            received.append(("verdict", decode_json(msg)))
            done.set()

        async def on_out(msg: Msg) -> None:
            received.append(("out", decode_json(msg)))

        await subscribe(nc, Subjects.GATEKEEPER_VERDICT, on_verdict)
        await subscribe(nc, Subjects.GATEKEEPER_OUT, on_out)

        print(f"--> scenario={scenario} trace_id={request.trace_id}")
        await publish_json(
            nc, Subjects.GATEKEEPER_IN, request.model_dump(mode="json")
        )

        try:
            await asyncio.wait_for(done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            print("(timed out waiting for verdict)")
        # Give the 'out' subscription a moment in case the verdict raced ahead.
        await asyncio.sleep(0.25)

    if not received:
        print("(no messages received)")
        return 1

    for kind, body in received:
        print(f"<-- {kind}: {body}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(SCENARIOS.keys()))
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    return asyncio.run(_run(args.scenario, timeout=args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
