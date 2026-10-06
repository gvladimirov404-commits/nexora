from unittest.mock import patch

from web3 import Web3

from integration.orchestrator import prepare_verification
from verifier.models import Evidence, Policy, VerificationResult


def test_prepare_verification():
    repository_url = "https://github.com/example/project"

    policy = Policy(
        version="1.0",
        repository_url=repository_url,
        task_type="github_repository",
        repository_visibility="public",
        required_files=[],
    )

    evidence = Evidence(
        repository_url=repository_url,
        commit_sha="abc123",
    )

    result = VerificationResult(
        repository_exists=True,
        repository_public=True,
        required_files={},
        passed=True,
    )

    with patch(
        "integration.orchestrator.create_verification_report"
    ) as mock_report:
        from verifier.report import VerificationReport
        from verifier.canonical import evidence_hash, policy_hash, verification_hash

        report = VerificationReport(
            policy_hash=policy_hash(policy),
            evidence_hash=evidence_hash(evidence),
            verification_hash=verification_hash(result),
            result=result,
        )
        mock_report.return_value = report

        prepared = prepare_verification(
            web3=Web3(),
            contract_address="0x0000000000000000000000000000000000000001",
            task_id=7,
            policy=policy,
            evidence=evidence,
        )

    assert prepared.report is report
    assert prepared.report.result.passed is True
    assert prepared.submit_calldata.startswith("0x")
    assert prepared.verify_calldata.startswith("0x")
    mock_report.assert_called_once_with(
        policy=policy,
        evidence=evidence,
    )
