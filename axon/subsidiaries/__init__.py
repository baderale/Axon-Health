"""The Axon Health subsidiaries built so far, by bus id."""

from collections.abc import Callable

from axon.subsidiaries import clinical_research, pharma
from axon.subsidiary.supervisor import Supervisor

SUBSIDIARIES: dict[str, Callable[[], Supervisor]] = {
    clinical_research.NAME: clinical_research.build,
    pharma.NAME: pharma.build,
}

__all__ = ["SUBSIDIARIES"]
