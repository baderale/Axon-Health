"""Axon Clinical Research.

Departments (this milestone):
  - Intake: turns a free-text case into structured fields.
  - Clinical SME: answers the clinical question, consulting Axon Pharma's
    Pharma Research department for anything drug- or dosing-related.

The Compliance department on the org map arrives in a later milestone.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from axon.subsidiary.department import (
    Consult,
    ConsultationError,
    ask_model,
    parse_json_object,
)
from axon.subsidiary.supervisor import Supervisor

NAME = "clinical_research"

# Identifiers are pulled into named fields deterministically, so the record
# structure never depends on the model. The gatekeeper redacts them in transit.
_PATIENT_ID = re.compile(r"(?i)\bpatient[\s_-]?id\b\s*[:#=]?\s*(\d{3,})")
_MRN = re.compile(r"(?i)\bMRN\b\s*[:#=]?\s*([A-Z0-9-]{4,})")
_DOSING_WORDS = re.compile(r"(?i)\b(dose|dosing|dosage|mg|titrat\w*|max(imum)? daily)\b")


class Intake:
    name = "intake"
    description = "Turns a free-text clinical case into structured fields."
    model = "intake.v0"

    async def handle(self, task: dict[str, Any], consult: Consult) -> dict[str, Any]:
        case = str(task.get("case", ""))
        patient_id = _PATIENT_ID.search(case)
        mrn = _MRN.search(case)

        extracted = parse_json_object(await ask_model(self.model, case)) or {}
        question = extracted.get("question") or case
        return {
            "patient_id": patient_id.group(1) if patient_id else None,
            "mrn": mrn.group(1) if mrn else None,
            "question": question,
            "condition": extracted.get("condition"),
            "drug": extracted.get("drug"),
        }


class _SMEState(TypedDict, total=False):
    task: dict[str, Any]
    pharma_notes: dict[str, Any] | None
    pharma_error: dict[str, Any] | None
    answer: str


class ClinicalSME:
    name = "clinsme"
    description = "Answers clinical questions; consults Axon Pharma on drugs and dosing."
    model = "clinsme.v0"

    def __init__(self) -> None:
        self._graph = self._build()

    @staticmethod
    def _needs_pharma(task: dict[str, Any]) -> bool:
        return bool(task.get("drug")) or bool(_DOSING_WORDS.search(str(task.get("question", ""))))

    def _build(self):
        async def consult_pharma(state: _SMEState, config: RunnableConfig) -> _SMEState:
            consult: Consult = config["configurable"]["consult"]
            task = state["task"]
            # The full record goes out; stripping identifiers is the
            # gatekeeper's job, and the audit trail shows it happening.
            request = {
                k: task.get(k) for k in ("patient_id", "mrn", "condition", "drug", "question")
            }
            try:
                return {"pharma_notes": await consult("pharma", "research", request)}
            except ConsultationError as exc:
                return {"pharma_error": exc.as_dict()}

        async def answer(state: _SMEState) -> _SMEState:
            error = state.get("pharma_error")
            if error:
                # No dosing guidance without the pharmacology consult.
                detail = error.get("coaching_message") or error.get("reason") or ""
                return {
                    "answer": (
                        f"Axon Pharma could not be consulted ({error['decision']}). "
                        f"No dosing guidance given. {detail}"
                    ).strip()
                }
            task = state["task"]
            notes = state.get("pharma_notes")
            context = (
                f"Pharmacology notes from Axon Pharma:\n{json.dumps(notes, default=str)}"
                if notes
                else None
            )
            text = await ask_model(self.model, str(task.get("question", "")), extra_context=context)
            return {"answer": text.strip()}

        def route(state: _SMEState) -> str:
            return "consult_pharma" if self._needs_pharma(state["task"]) else "answer"

        graph: StateGraph = StateGraph(_SMEState)
        graph.add_node("consult_pharma", consult_pharma)
        graph.add_node("answer", answer)
        graph.add_conditional_edges(START, route, ["consult_pharma", "answer"])
        graph.add_edge("consult_pharma", "answer")
        graph.add_edge("answer", END)
        return graph.compile()

    async def handle(self, task: dict[str, Any], consult: Consult) -> dict[str, Any]:
        final = await self._graph.ainvoke(
            {"task": task}, config={"configurable": {"consult": consult}}
        )
        return {
            "answer": final["answer"],
            "pharma_consulted": bool(final.get("pharma_notes")),
            "pharma_error": final.get("pharma_error"),
        }


def build() -> Supervisor:
    return Supervisor(NAME, [Intake(), ClinicalSME()], entry_pipeline=["intake", "clinsme"])
