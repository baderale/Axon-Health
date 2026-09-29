"""Supervisor: the one agent per subsidiary that routes work to departments.

The Supervisor is a small LangGraph: ``route`` picks the department pipeline
for a task, then ``run_step`` runs each department in order, merging every
department's output into the task the next one sees. The ``consult`` function
travels in the graph config, so departments can reach other subsidiaries only
through what the runtime gives them.
"""

from __future__ import annotations

from typing import Any, TypedDict

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from axon.subsidiary.department import Consult, Department

log = structlog.get_logger(__name__)


class SupervisorState(TypedDict, total=False):
    task: dict[str, Any]
    pipeline: list[str]
    step: int
    error: str


class Supervisor:
    def __init__(
        self,
        name: str,
        departments: list[Department],
        *,
        entry_pipeline: list[str],
    ) -> None:
        self.name = name
        self.departments: dict[str, Department] = {d.name: d for d in departments}
        unknown = [d for d in entry_pipeline if d not in self.departments]
        if unknown:
            raise ValueError(f"{name}: entry pipeline names unknown departments {unknown}")
        self.entry_pipeline = list(entry_pipeline)
        self._graph = self._build()

    def _build(self):
        def route(state: SupervisorState) -> SupervisorState:
            task = state["task"]
            requested = task.get("department")
            pipeline = [requested] if requested else self.entry_pipeline
            missing = [d for d in pipeline if d not in self.departments]
            if missing:
                return {"pipeline": [], "step": 0, "error": f"Unknown department {missing[0]!r}"}
            return {"pipeline": pipeline, "step": 0}

        async def run_step(state: SupervisorState, config: RunnableConfig) -> SupervisorState:
            consult: Consult = config["configurable"]["consult"]
            dept = self.departments[state["pipeline"][state["step"]]]
            log.info("supervisor.department", subsidiary=self.name, department=dept.name)
            output = await dept.handle(state["task"], consult)
            return {"task": {**state["task"], **output}, "step": state["step"] + 1}

        def next_step(state: SupervisorState) -> str:
            if state.get("error") or state["step"] >= len(state["pipeline"]):
                return END
            return "run_step"

        graph: StateGraph = StateGraph(SupervisorState)
        graph.add_node("route", route)
        graph.add_node("run_step", run_step)
        graph.add_edge(START, "route")
        graph.add_conditional_edges("route", next_step, ["run_step", END])
        graph.add_conditional_edges("run_step", next_step, ["run_step", END])
        return graph.compile()

    async def run(self, task: dict[str, Any], consult: Consult) -> dict[str, Any]:
        """Run a task through the department pipeline and return the merged result.

        ``task["department"]`` selects a single department (inbound requests
        from other subsidiaries); otherwise the entry pipeline runs.
        """
        final = await self._graph.ainvoke(
            {"task": task}, config={"configurable": {"consult": consult}}
        )
        if final.get("error"):
            return {"error": final["error"]}
        result = dict(final["task"])
        result.pop("department", None)
        return result
