"""Axon Pharma.

Departments (this milestone):
  - Pharma Research: answers drug and dosing questions from other subsidiaries.

The Marketing department on the org map arrives in a later milestone.
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from axon.subsidiary.department import Consult, ask_model
from axon.subsidiary.supervisor import Supervisor

NAME = "pharma"


class _ResearchState(TypedDict, total=False):
    task: dict[str, Any]
    answer: str


class PharmaResearch:
    name = "research"
    description = "Drug and dosing questions; current pharmaceutical research."
    model = "pharma-research.v0"

    def __init__(self) -> None:
        self._graph = self._build()

    def _build(self):
        async def answer(state: _ResearchState) -> _ResearchState:
            task = state["task"]
            question = {k: task.get(k) for k in ("question", "drug", "condition")}
            text = await ask_model(self.model, json.dumps(question, default=str))
            return {"answer": text.strip()}

        graph: StateGraph = StateGraph(_ResearchState)
        graph.add_node("answer", answer)
        graph.add_edge(START, "answer")
        graph.add_edge("answer", END)
        return graph.compile()

    async def handle(self, task: dict[str, Any], consult: Consult) -> dict[str, Any]:
        final = await self._graph.ainvoke({"task": task})
        return {"answer": final["answer"]}


def build() -> Supervisor:
    return Supervisor(NAME, [PharmaResearch()], entry_pipeline=["research"])
