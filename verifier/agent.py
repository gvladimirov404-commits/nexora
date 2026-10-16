from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from verifier.engine import is_task_type_registered, verify_registered_task
from verifier.registry import UniversalVerificationResult


@dataclass(frozen=True)
class AgentTask:
    task_type: str
    policy: Any
    evidence: Any


@dataclass(frozen=True)
class AgentPlan:
    task_type: str
    tool_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentResult:
    task_type: str
    verification: UniversalVerificationResult
    tool_results: tuple[Any, ...] = ()

    @property
    def passed(self) -> bool:
        return self.verification.status == "PASS"


AgentTool = Callable[[AgentTask], Any]
AgentPlanner = Callable[[AgentTask], AgentPlan]

def build_default_plan(task: AgentTask) -> AgentPlan:
    """Choose a route only when a verifier is registered for the task type."""
    if not is_task_type_registered(task.task_type):
        raise ValueError(f"Unsupported task type: {task.task_type}")
    return AgentPlan(task_type=task.task_type)



class AgentToolRegistry:
    """Executes only explicitly registered tools."""

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, name: str, tool: AgentTool) -> None:
        if not name.strip():
            raise ValueError("Tool name must not be empty")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        if not callable(tool):
            raise TypeError("Tool must be callable")
        self._tools[name] = tool

    def validate_plan(self, plan: AgentPlan) -> None:
        if not plan.task_type.strip():
            raise ValueError("Plan task_type must not be empty")
        if len(set(plan.tool_names)) != len(plan.tool_names):
            raise ValueError("Plan contains duplicate tools")
        for name in plan.tool_names:
            if name not in self._tools:
                raise ValueError(f"Tool not allowed or registered: {name}")

    def execute(
        self, plan: AgentPlan, task: AgentTask
    ) -> tuple[Any, ...]:
        self.validate_plan(plan)
        # Validate every tool before running any of them.
        return tuple(self._tools[name](task) for name in plan.tool_names)


def run_task(
    task: AgentTask,
    plan: AgentPlan | None = None,
    tool_registry: AgentToolRegistry | None = None,
    planner: AgentPlanner | None = None,
    evidence_builder: Callable[[AgentTask, tuple[Any, ...]], Any] | None = None,
) -> AgentResult:
    """Plan optionally, execute only registered tools, then verify the task."""
    if not task.task_type.strip():
        raise ValueError("task_type must not be empty")

    if getattr(task.policy, "task_type", None) != task.task_type:
        raise ValueError("Task type does not match policy task_type")

    if not is_task_type_registered(task.task_type):
        raise ValueError(f"Unsupported task type: {task.task_type}")

    if plan is not None and planner is not None:
        raise ValueError("Provide either plan or planner, not both")

    if planner is not None:
        if not callable(planner):
            raise TypeError("planner must be callable")
        plan = planner(task)
        if not isinstance(plan, AgentPlan):
            raise TypeError("planner must return an AgentPlan")
    elif plan is None:
        plan = build_default_plan(task)

    if plan.task_type != task.task_type:
        raise ValueError("Plan task type does not match task type")

    if evidence_builder is not None:
        if not callable(evidence_builder):
            raise TypeError("evidence_builder must be callable")
        if not plan.tool_names:
            raise ValueError("evidence_builder requires at least one planned tool")

    tool_results: tuple[Any, ...] = ()
    if plan.tool_names:
        if tool_registry is None:
            raise ValueError("A tool registry is required for this plan")
        tool_results = tool_registry.execute(plan, task)

    evidence = task.evidence
    if evidence_builder is not None:
        evidence = evidence_builder(task, tool_results)

    result = verify_registered_task(task.policy, evidence)
    return AgentResult(
        task_type=task.task_type,
        verification=result,
        tool_results=tool_results,
    )
