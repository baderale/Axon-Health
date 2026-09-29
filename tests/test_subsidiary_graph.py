"""Unit tests for the subsidiary template and the first two subsidiaries.

No infrastructure: department models are stubbed and ``consult`` is a local
fake, so these run anywhere.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from axon.subsidiaries import clinical_research, pharma
from axon.subsidiary import department as department_mod
from axon.subsidiary.department import ConsultationError

CASE = (
    "Patient_id 12345, MRN MRN-AX-99182, 58 y/o with hepatic impairment. "
    "What is the safe dosing window for acetaminophen?"
)


class _FakeClient:
    def __init__(self, logical_name: str, replies: dict[str, str], calls: list) -> None:
        self.logical_name = logical_name
        self.replies = replies
        self.calls = calls

    def chat(self, user_message: str, *, extra_context: str | None = None) -> str:
        self.calls.append((self.logical_name, user_message, extra_context))
        return self.replies[self.logical_name]


@pytest.fixture
def models(monkeypatch):
    """Stub every department model. Tests edit ``state['replies']`` as needed."""
    state = {
        "replies": {
            "intake.v0": json.dumps(
                {
                    "question": "Safe acetaminophen dosing in hepatic impairment?",
                    "condition": "hepatic impairment",
                    "drug": "acetaminophen",
                }
            ),
            "clinsme.v0": "Keep acetaminophen at or below 2 g/day, per Axon Pharma.",
            "pharma-research.v0": "Limit to 2 g/day in hepatic impairment.",
        },
        "calls": [],
    }
    monkeypatch.setattr(
        department_mod,
        "get_client",
        lambda name: _FakeClient(name, state["replies"], state["calls"]),
    )
    return state


async def test_clinical_research_pipeline_consults_pharma(models):
    consulted: list[tuple[str, str, dict]] = []

    async def consult(target, dept, payload):
        consulted.append((target, dept, payload))
        return {"answer": "Limit to 2 g/day in hepatic impairment."}

    result = await clinical_research.build().run({"case": CASE}, consult)

    assert result["patient_id"] == "12345"
    assert result["mrn"] == "MRN-AX-99182"
    assert result["drug"] == "acetaminophen"
    assert result["pharma_consulted"] is True
    assert result["pharma_error"] is None
    assert "2 g/day" in result["answer"]

    # The Supervisor's consult went to Pharma Research with the full record;
    # redaction is the gatekeeper's job, not the department's.
    [(target, dept, payload)] = consulted
    assert (target, dept) == ("pharma", "research")
    assert payload["patient_id"] == "12345"

    # Clinical SME saw Pharma's notes as context.
    clinsme_calls = [c for c in models["calls"] if c[0] == "clinsme.v0"]
    assert clinsme_calls and "2 g/day" in clinsme_calls[0][2]


async def test_refused_consult_returns_error_without_dosing_advice(models):
    async def consult(target, dept, payload):
        raise ConsultationError(
            "coach", "Borderline request", coaching_message="Ask without identifiers."
        )

    result = await clinical_research.build().run({"case": CASE}, consult)

    assert result["pharma_consulted"] is False
    assert result["pharma_error"]["decision"] == "coach"
    assert "No dosing guidance" in result["answer"]
    assert not [c for c in models["calls"] if c[0] == "clinsme.v0"]


async def test_non_drug_question_skips_pharma(models):
    models["replies"]["intake.v0"] = json.dumps(
        {"question": "Which imaging is first-line for suspected appendicitis?", "drug": None}
    )

    async def consult(target, dept, payload):
        raise AssertionError("should not consult Pharma")

    result = await clinical_research.build().run({"case": "Imaging for appendicitis?"}, consult)
    assert result["pharma_consulted"] is False


async def test_intake_falls_back_to_raw_case_when_model_output_is_not_json(models):
    models["replies"]["intake.v0"] = "Sorry, I can't format that."

    async def consult(target, dept, payload):
        return {"answer": "ok"}

    result = await clinical_research.build().run({"case": CASE}, consult)
    assert result["question"] == CASE
    # Still a dosing question, so Pharma is still consulted.
    assert result["pharma_consulted"] is True


async def test_pharma_answers_a_single_department_request(models):
    async def consult(target, dept, payload):
        raise AssertionError("Pharma Research does not consult anyone")

    result = await pharma.build().run(
        {"department": "research", "question": "Max acetaminophen?", "patient_id": "[REDACTED]"},
        consult,
    )
    assert result["answer"] == "Limit to 2 g/day in hepatic impairment."
    assert "department" not in result


async def test_unknown_department_is_an_error_not_a_crash(models):
    async def consult(target, dept, payload):
        raise AssertionError

    result = await pharma.build().run({"department": "marketing"}, consult)
    assert "Unknown department" in result["error"]


# ---- single-publisher invariant ------------------------------------------

_ROOT = Path(__file__).resolve().parents[1] / "axon"
_FORBIDDEN = ("axon.bus", "axon.subsidiary.runtime", "nats")


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize(
    "path",
    [
        _ROOT / "subsidiary" / "department.py",
        _ROOT / "subsidiary" / "supervisor.py",
        *sorted(p for p in (_ROOT / "subsidiaries").glob("*.py") if p.name != "run.py"),
    ],
    ids=lambda p: p.relative_to(_ROOT).as_posix(),
)
def test_departments_and_supervisors_never_touch_the_bus(path):
    bad = {
        name
        for name in _imports(path)
        if any(name == f or name.startswith(f + ".") for f in _FORBIDDEN)
    }
    assert not bad, f"{path.name} imports {sorted(bad)}; only the runtime may publish"
