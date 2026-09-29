"""Start one subsidiary as a service.

    python -m axon.subsidiaries.run clinical_research
    python -m axon.subsidiaries.run pharma
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

import structlog

from axon.subsidiaries import SUBSIDIARIES
from axon.subsidiary.runtime import SubsidiaryRuntime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subsidiary", choices=sorted(SUBSIDIARIES))
    args = parser.parse_args(argv)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, os.environ.get("LOG_LEVEL", "INFO"))
        )
    )
    runtime = SubsidiaryRuntime(SUBSIDIARIES[args.subsidiary]())
    asyncio.run(runtime.run_forever())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
