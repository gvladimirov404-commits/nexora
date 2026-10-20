from unittest.mock import patch

from web3 import Web3

from integration.contract import create_contract
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
            result_hash=evidence_hash(evidence),
            evidence_hash="ab" * 32,
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
    submit_contract = create_contract(
        Web3(),
        "0x0000000000000000000000000000000000000001",
    )
    _, submit_args = submit_contract.decode_function_input(
        prepared.submit_calldata
    )
    assert submit_args["resultHash"].hex() == prepared.report.result_hash
    assert prepared.verify_calldata.startswith("0x")
    verify_contract = create_contract(
        Web3(),
        "0x0000000000000000000000000000000000000001",
    )
    _, verify_args = verify_contract.decode_function_input(
        prepared.verify_calldata
    )
    assert verify_args["taskId"] == 7
    assert verify_args["passed"] is True
    assert verify_args["evidenceHash"].hex() == prepared.report.evidence_hash
    mock_report.assert_called_once_with(
        policy=policy,
        evidence=evidence,
    )


def test_prepared_verification_calldata_runs_through_sender(monkeypatch):
    from unittest.mock import MagicMock, Mock

    import integration.transaction_sender as sender_module
    from integration.transaction_sender import TransactionResult
    from integration.orchestrator import prepare_verification

    web3 = Web3()
    sender_web3 = MagicMock()
    agent_address = "0x0000000000000000000000000000000000000001"
    verifier_address = "0x0000000000000000000000000000000000000003"
    contract_address = "0x0000000000000000000000000000000000000002"
    repository_url = "https://github.com/example/project"

    policy = Policy(
        version="1.0",
        repository_url=repository_url,
        task_type="github_repository",
        repository_visibility="public",
        required_files=["README.md"],
    )
    evidence = Evidence(repository_url=repository_url, commit_sha="abc123")

    repository_response = Mock(status_code=200)
    repository_response.json.return_value = {"private": False}

    with patch("verifier.github_checker.requests.get") as mock_get:
        mock_get.side_effect = [
            repository_response,
            Mock(status_code=200),
            Mock(status_code=200),
        ]
        prepared = prepare_verification(
            web3=web3,
            contract_address=contract_address,
            task_id=7,
            policy=policy,
            evidence=evidence,
        )

    requested_urls = [call.args[0] for call in mock_get.call_args_list]
    assert requested_urls == [
        "https://api.github.com/repos/example/project",
        "https://api.github.com/repos/example/project/commits/abc123",
        "https://api.github.com/repos/example/project/contents/README.md?ref=abc123",
    ]
    assert prepared.report.result.required_files == {"README.md": True}
    assert prepared.report.result.passed is True

    agent_account = MagicMock(address=agent_address)
    verifier_account = MagicMock(address=verifier_address)
    sender_web3.eth.chain_id = 421614
    sender_web3.eth.account.from_key.side_effect = lambda key: {
        "agent-test-key": agent_account,
        "verifier-test-key": verifier_account,
    }[key]

    expected_submit = TransactionResult("0x" + "11" * 32, 123, 42000, 1)
    expected_verify = TransactionResult("0x" + "22" * 32, 124, 43000, 1)
    mocked_sender = MagicMock(side_effect=[expected_submit, expected_verify])
    monkeypatch.setattr(
        sender_module, "send_calldata_transaction", mocked_sender
    )

    result = sender_module.send_verification_sequence(
        sender_web3,
        contract_address,
        agent_address,
        verifier_address,
        prepared.submit_calldata,
        prepared.verify_calldata,
        agent_private_key="agent-test-key",
        verifier_private_key="verifier-test-key",
        expected_contract_address=contract_address,
    )

    assert result.succeeded
    assert mocked_sender.call_count == 2
    assert mocked_sender.call_args_list[0].args[3] == prepared.submit_calldata
    assert mocked_sender.call_args_list[1].args[3] == prepared.verify_calldata
