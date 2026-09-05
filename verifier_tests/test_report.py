from unittest.mock import patch

from verifier.canonical import (
    evidence_hash,
    policy_hash,
    verification_hash,
)
from verifier.models import (
    Evidence,
    Policy,
    VerificationResult,
)
from verifier.report import create_verification_report


def make_policy() -> Policy:
    return Policy(
        version="v1",
        task_type="github_repository",
        repository_visibility="public",
        required_files=["README.md", "LICENSE"],
    )


def make_evidence() -> Evidence:
    return Evidence(
        repository_url="https://github.com/example/project",
        commit_sha="abc123",
    )


@patch("verifier.report.verify_task")
def test_create_verification_report(mock_verify_task):
    result = VerificationResult(
        repository_exists=True,
        repository_public=True,
        required_files={
            "README.md": True,
            "LICENSE": True,
        },
        passed=True,
    )

    mock_verify_task.return_value = result

    policy = make_policy()
    evidence = make_evidence()

    report = create_verification_report(
        policy=policy,
        evidence=evidence,
    )

    assert report.policy_hash == policy_hash(policy)
    assert report.evidence_hash == evidence_hash(evidence)
    assert report.verification_hash == verification_hash(result)
    assert report.result == result

    mock_verify_task.assert_called_once_with(
        policy=policy,
        evidence=evidence,
    )
