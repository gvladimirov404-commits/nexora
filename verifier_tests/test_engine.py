from unittest.mock import patch

import pytest

from verifier.engine import verify_task
from verifier.models import Evidence, Policy, VerificationResult


def make_policy():
    return Policy(
        version="1.0",
        task_type="github_repository",
        repository_visibility="public",
        required_files=["README.md", "LICENSE"],
    )


def make_evidence():
    return Evidence(
        repository_url="https://github.com/example/project",
        commit_sha="abc123",
    )


@patch("verifier.engine.check_github_repository")
def test_verify_task_delegates_to_github_checker(mock_checker):
    expected = VerificationResult(
        repository_exists=True,
        repository_public=True,
        required_files={
            "README.md": True,
            "LICENSE": True,
        },
        passed=True,
    )

    mock_checker.return_value = expected

    result = verify_task(
        make_policy(),
        make_evidence(),
    )

    assert result == expected
    mock_checker.assert_called_once_with(
        policy=make_policy(),
        evidence=make_evidence(),
    )


def test_verify_task_rejects_unsupported_task_type():
    policy = Policy(
        version="1.0",
        task_type="unknown_task",
        repository_visibility="public",
        required_files=[],
    )

    with pytest.raises(ValueError, match="Unsupported task type"):
        verify_task(policy, make_evidence())


def test_verify_task_rejects_non_public_policy():
    policy = Policy(
        version="1.0",
        task_type="github_repository",
        repository_visibility="private",
        required_files=[],
    )

    with pytest.raises(
        ValueError,
        match="Only public GitHub repositories are supported",
    ):
        verify_task(policy, make_evidence())
