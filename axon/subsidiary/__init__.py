"""Subsidiary template: departments, the Supervisor that routes to them, and the
runtime that is the subsidiary's only publisher on the Inter-Subsidiary Bus."""

from axon.subsidiary.department import Consult, ConsultationError, Department
from axon.subsidiary.supervisor import Supervisor

__all__ = ["Consult", "ConsultationError", "Department", "Supervisor"]
