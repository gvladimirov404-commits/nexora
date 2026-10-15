from unittest.mock import patch

from verifier.agent import AgentTask, run_task
from verifier.models import Evidence, Policy, VerificationResult


def test_agent_uses_registered_github_repository_verifier():
    policy = Policy(
        version="1",
        repository_url="https://github.com/example/project",
        task_type="github_repository",
        repository_visibility="public",
        required_files=["README.md"],
    )
    evidence = Evidence(
        repository_url="https://github.com/example/project",
        commit_sha="abc123",
    )
    expected = VerificationResult(
        repository_exists=True,
        repository_public=True,
        required_files={"README.md": True},
        passed=True,
    )

    with patch(
        "verifier.engine.check_github_repository",
        return_value=expected,
    ) as checker:
        result = run_task(AgentTask("github_repository", policy, evidence))

    checker.assert_called_once_with(policy=policy, evidence=evidence)
    assert result.task_type == "github_repository"
    assert result.passed is True
    assert result.verification.status == "PASS"
    assert result.verification.details["required_files"] == {"README.md": True}
