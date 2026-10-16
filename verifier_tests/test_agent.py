from dataclasses import dataclass

import pytest

from verifier.agent import (
    AgentPlan,
    build_default_plan,
    AgentTask,
    AgentToolRegistry,
    run_task,
)


@dataclass(frozen=True)
class ReportPolicy:
    version: str
    task_type: str
    required_sections: list[str]


@dataclass(frozen=True)
class ReportEvidence:
    content: str | None


def make_task(content="# Summary\nOverview\n# Conclusion\nComplete."):
    policy = ReportPolicy(
        version="1",
        task_type="report",
        required_sections=["Summary", "Conclusion"],
    )
    evidence = ReportEvidence(content=content)
    return AgentTask("report", policy, evidence)


def test_agent_runs_registered_report_verifier():
    result = run_task(make_task())

    assert result.task_type == "report"
    assert result.passed is True
    assert result.verification.status == "PASS"


def test_agent_returns_failure_for_incomplete_report():
    result = run_task(make_task("# Summary\nOverview"))

    assert result.passed is False
    assert result.verification.status == "FAIL"


def test_agent_rejects_task_policy_type_mismatch():
    task = make_task()

    with pytest.raises(ValueError, match="does not match"):
        run_task(AgentTask("github_tests", task.policy, task.evidence))


def test_agent_rejects_unknown_task_type():
    task = make_task()
    policy = ReportPolicy(
        version="1",
        task_type="unknown",
        required_sections=["Summary"],
    )

    with pytest.raises(ValueError, match="Unsupported task type"):
        run_task(AgentTask("unknown", policy, task.evidence))


def test_agent_executes_registered_tool_from_plan():
    task = make_task()
    registry = AgentToolRegistry()
    calls = []

    registry.register(
        "inspect_report",
        lambda received_task: calls.append(received_task.task_type) or "inspected",
    )

    plan = AgentPlan("report", ("inspect_report",))
    result = run_task(task, plan, registry)

    assert calls == ["report"]
    assert result.tool_results == ("inspected",)
    assert result.passed is True


def test_agent_rejects_unregistered_tool():
    task = make_task()
    registry = AgentToolRegistry()
    plan = AgentPlan("report", ("unknown_tool",))

    with pytest.raises(ValueError, match="not allowed or registered"):
        run_task(task, plan, registry)


def test_agent_rejects_plan_for_another_task_type():
    task = make_task()
    plan = AgentPlan("github_tests")

    with pytest.raises(ValueError, match="Plan task type"):
        run_task(task, plan)


def test_agent_requires_registry_when_plan_uses_tools():
    task = make_task()
    plan = AgentPlan("report", ("inspect_report",))

    with pytest.raises(ValueError, match="registry is required"):
        run_task(task, plan)


def test_agent_validates_all_tools_before_executing_any():
    task = make_task()
    registry = AgentToolRegistry()
    calls = []

    registry.register("safe_tool", lambda _: calls.append("called"))
    plan = AgentPlan("report", ("safe_tool", "unknown_tool"))

    with pytest.raises(ValueError, match="not allowed or registered"):
        run_task(task, plan, registry)

    assert calls == []


def test_agent_rejects_duplicate_tool_registration():
    registry = AgentToolRegistry()
    registry.register("inspect_report", lambda _: "ok")

    with pytest.raises(ValueError, match="already registered"):
        registry.register("inspect_report", lambda _: "another")


def test_agent_uses_supplied_planner():
    task = make_task()
    registry = AgentToolRegistry()
    calls = []
    registry.register(
        "inspect_report",
        lambda received_task: calls.append(received_task.task_type) or "inspected",
    )

    def planner(received_task):
        assert received_task is task
        return AgentPlan("report", ("inspect_report",))

    result = run_task(task, tool_registry=registry, planner=planner)

    assert calls == ["report"]
    assert result.tool_results == ("inspected",)
    assert result.passed is True


def test_agent_rejects_planner_for_another_task_type():
    task = make_task()

    with pytest.raises(ValueError, match="Plan task type"):
        run_task(task, planner=lambda _: AgentPlan("github_tests"))


def test_agent_rejects_planner_returning_wrong_type():
    task = make_task()

    with pytest.raises(TypeError, match="must return an AgentPlan"):
        run_task(task, planner=lambda _: "not a plan")


def test_agent_rejects_plan_and_planner_together():
    task = make_task()

    with pytest.raises(ValueError, match="either plan or planner"):
        run_task(
            task,
            plan=AgentPlan("report"),
            planner=lambda _: AgentPlan("report"),
        )


def test_agent_planner_cannot_execute_unregistered_tools():
    task = make_task()
    registry = AgentToolRegistry()
    calls = []
    registry.register("safe_tool", lambda _: calls.append("called"))

    def planner(_):
        return AgentPlan("report", ("safe_tool", "unknown_tool"))

    with pytest.raises(ValueError, match="not allowed or registered"):
        run_task(task, tool_registry=registry, planner=planner)

    assert calls == []

def test_default_planner_routes_supported_task_types():
    for task_type in ("report", "github_repository", "github_tests"):
        plan = build_default_plan(
            AgentTask(task_type, type("Policy", (), {"task_type": task_type})(), None)
        )
        assert plan.task_type == task_type
        assert plan.tool_names == ()


def test_default_planner_accepts_registered_external_task_type():
    from types import SimpleNamespace

    from verifier.engine import register_task_verifier
    from verifier.registry import UniversalVerificationResult

    task_type = "agent_dynamic_planner_test"
    register_task_verifier(
        task_type,
        lambda policy, evidence: UniversalVerificationResult(
            status="PASS",
            policy_hash="p",
            evidence_hash="e",
            verification_hash="v",
            details={},
        ),
    )

    plan = build_default_plan(
        AgentTask(task_type, SimpleNamespace(task_type=task_type), None)
    )

    assert plan.task_type == task_type
    assert plan.tool_names == ()


def test_default_planner_rejects_unknown_task_type():
    task = AgentTask("unknown_task", object(), object())

    with pytest.raises(ValueError, match="Unsupported task type"):
        build_default_plan(task)


def test_agent_runs_externally_registered_task_type():
    from types import SimpleNamespace

    from verifier.engine import register_task_verifier
    from verifier.registry import UniversalVerificationResult

    task_type = "agent_external_end_to_end_test"
    register_task_verifier(
        task_type,
        lambda policy, evidence: UniversalVerificationResult(
            status="PASS" if evidence.proof == policy.expected_proof else "FAIL",
            policy_hash="policy-hash",
            evidence_hash="evidence-hash",
            verification_hash="verification-hash",
            details={"checker": "external"},
        ),
    )

    task = AgentTask(
        task_type,
        SimpleNamespace(task_type=task_type, expected_proof="valid"),
        SimpleNamespace(proof="valid"),
    )
    result = run_task(task)

    assert result.task_type == task_type
    assert result.passed is True
    assert result.verification.status == "PASS"
    assert result.verification.details["checker"] == "external"


def test_unregistered_task_is_rejected_before_tool_execution():
    from types import SimpleNamespace
    import pytest

    task_type = "agent_unregistered_safety_test"
    task = AgentTask(
        task_type,
        SimpleNamespace(task_type=task_type),
        SimpleNamespace(),
    )
    called = []
    tools = AgentToolRegistry()
    tools.register("must_not_run", lambda task: called.append(True))
    plan = AgentPlan(task_type=task_type, tool_names=("must_not_run",))

    with pytest.raises(ValueError, match="Unsupported task type"):
        run_task(task, plan=plan, tool_registry=tools)

    assert called == []


def test_agent_can_verify_evidence_built_from_tool_results():
    task = make_task("# Summary\nIncomplete")
    registry = AgentToolRegistry()
    tool_report = "# Summary\nOverview\n# Conclusion\nComplete."

    registry.register(
        "collect_report",
        lambda received_task: tool_report,
    )

    result = run_task(
        task,
        plan=AgentPlan("report", ("collect_report",)),
        tool_registry=registry,
        evidence_builder=lambda received_task, results: ReportEvidence(
            content=results[0]
        ),
    )

    assert result.tool_results == (tool_report,)
    assert result.passed is True
    assert result.verification.details["required_sections"] == {
        "Summary": True,
        "Conclusion": True,
    }

def test_agent_rejects_non_callable_evidence_builder():
    with pytest.raises(TypeError, match="evidence_builder must be callable"):
        run_task(make_task(), evidence_builder="not callable")


def test_agent_rejects_evidence_builder_without_planned_tools():
    with pytest.raises(ValueError, match="at least one planned tool"):
        run_task(
            make_task(),
            plan=AgentPlan("report"),
            evidence_builder=lambda task, results: task.evidence,
        )
