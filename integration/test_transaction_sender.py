from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes
from web3 import Web3

from integration.transaction_sender import send_calldata_transaction


SENDER = "0x0000000000000000000000000000000000000001"
CONTRACT = "0x0000000000000000000000000000000000000002"


def make_web3():
    web3 = MagicMock()
    web3.eth.chain_id = 421614
    web3.eth.gas_price = 1
    web3.eth.get_transaction_count.return_value = 7
    web3.eth.estimate_gas.return_value = 50_000

    web3.eth.account.from_key.return_value.address = SENDER
    web3.eth.account.sign_transaction.return_value.raw_transaction = b"\x12\x34"

    web3.eth.send_raw_transaction.return_value = HexBytes("0x" + "ab" * 32)
    web3.eth.wait_for_transaction_receipt.return_value = {
        "status": 1,
        "blockNumber": 123,
        "gasUsed": 42_000,
    }
    return web3


def test_sends_and_confirms_transaction():
    web3 = make_web3()

    result = send_calldata_transaction(
        web3, CONTRACT, SENDER, "0x1234", private_key="test-key"
    )

    assert result.succeeded
    assert result.tx_hash == "0x" + "ab" * 32
    assert result.block_number == 123
    assert result.gas_used == 42_000
    web3.eth.send_raw_transaction.assert_called_once_with(b"\x12\x34")
    web3.eth.wait_for_transaction_receipt.assert_called_once()


def test_rejects_wrong_network_before_signing():
    web3 = make_web3()
    web3.eth.chain_id = 1

    with pytest.raises(ValueError, match="Wrong network"):
        send_calldata_transaction(
            web3, CONTRACT, SENDER, "0x1234", private_key="test-key"
        )

    web3.eth.account.sign_transaction.assert_not_called()
    web3.eth.send_raw_transaction.assert_not_called()


def test_rejects_key_that_does_not_match_sender():
    web3 = make_web3()
    web3.eth.account.from_key.return_value.address = CONTRACT

    with pytest.raises(ValueError, match="does not match"):
        send_calldata_transaction(
            web3, CONTRACT, SENDER, "0x1234", private_key="test-key"
        )

    web3.eth.send_raw_transaction.assert_not_called()


def test_requires_key_without_environment_variable(monkeypatch):
    monkeypatch.delenv("NEXORA_PRIVATE_KEY", raising=False)
    web3 = make_web3()

    with pytest.raises(ValueError, match="NEXORA_PRIVATE_KEY"):
        send_calldata_transaction(web3, CONTRACT, SENDER, "0x1234")

    web3.eth.send_raw_transaction.assert_not_called()


def test_reports_reverted_transaction():
    web3 = make_web3()
    web3.eth.wait_for_transaction_receipt.return_value = {
        "status": 0,
        "blockNumber": 124,
        "gasUsed": 30_000,
    }

    result = send_calldata_transaction(
        web3, CONTRACT, SENDER, "0x1234", private_key="test-key"
    )

    assert not result.succeeded
    assert result.status == 0

def test_rejects_unexpected_contract_before_signing_or_sending():
    web3 = make_web3()

    with pytest.raises(ValueError, match="Wrong contract address"):
        send_calldata_transaction(
            web3,
            CONTRACT,
            SENDER,
            "0x1234",
            private_key="test-key",
            expected_contract_address=SENDER,
        )

    web3.eth.account.sign_transaction.assert_not_called()
    web3.eth.send_raw_transaction.assert_not_called()



def test_send_verification_sequence_success(monkeypatch):
    import integration.transaction_sender as sender_module

    verifier_address = "0x0000000000000000000000000000000000000003"
    agent_account = MagicMock()
    agent_account.address = SENDER
    verifier_account = MagicMock()
    verifier_account.address = verifier_address

    web3 = make_web3()
    web3.eth.account.from_key.side_effect = lambda key: {
        "agent-test-key": agent_account,
        "verifier-test-key": verifier_account,
    }[key]

    submit_selector = Web3.keccak(text="submitResult(uint256,bytes32)")[:4]
    verify_selector = Web3.keccak(text="verifyTask(uint256,bool,bytes32)")[:4]
    task_id = (7).to_bytes(32, "big")
    submit_calldata = "0x" + (
        submit_selector + task_id + b"\x11" * 32
    ).hex()
    verify_calldata = "0x" + (
        verify_selector + task_id + (1).to_bytes(32, "big") + b"\x22" * 32
    ).hex()

    expected_submit = sender_module.TransactionResult(
        "0x" + "11" * 32, 123, 42000, 1
    )
    expected_verify = sender_module.TransactionResult(
        "0x" + "22" * 32, 124, 43000, 1
    )
    mocked_sender = MagicMock(
        side_effect=[expected_submit, expected_verify]
    )
    monkeypatch.setattr(
        sender_module, "send_calldata_transaction", mocked_sender
    )

    result = sender_module.send_verification_sequence(
        web3,
        CONTRACT,
        SENDER,
        verifier_address,
        submit_calldata,
        verify_calldata,
        agent_private_key="agent-test-key",
        verifier_private_key="verifier-test-key",
        expected_contract_address=CONTRACT,
    )

    assert result.succeeded
    assert result.submit_result == expected_submit
    assert result.verify_result == expected_verify
    assert mocked_sender.call_count == 2
    assert mocked_sender.call_args_list[0].args[2] == SENDER
    assert mocked_sender.call_args_list[0].args[3] == submit_calldata
    assert mocked_sender.call_args_list[0].kwargs["private_key"] == "agent-test-key"
    assert mocked_sender.call_args_list[1].args[2] == verifier_address
    assert mocked_sender.call_args_list[1].args[3] == verify_calldata
    assert mocked_sender.call_args_list[1].kwargs["private_key"] == "verifier-test-key"


def test_send_verification_sequence_stops_after_failed_submit(monkeypatch):
    import integration.transaction_sender as sender_module

    verifier_address = "0x0000000000000000000000000000000000000003"
    agent_account = MagicMock()
    agent_account.address = SENDER
    verifier_account = MagicMock()
    verifier_account.address = verifier_address

    web3 = make_web3()
    web3.eth.account.from_key.side_effect = lambda key: {
        "agent-test-key": agent_account,
        "verifier-test-key": verifier_account,
    }[key]

    submit_selector = Web3.keccak(text="submitResult(uint256,bytes32)")[:4]
    verify_selector = Web3.keccak(text="verifyTask(uint256,bool,bytes32)")[:4]
    task_id = (7).to_bytes(32, "big")
    submit_calldata = "0x" + (
        submit_selector + task_id + b"\x11" * 32
    ).hex()
    verify_calldata = "0x" + (
        verify_selector + task_id + (1).to_bytes(32, "big") + b"\x22" * 32
    ).hex()

    failed_submit = sender_module.TransactionResult(
        "0x" + "33" * 32, 123, 42000, 0
    )
    mocked_sender = MagicMock(return_value=failed_submit)
    monkeypatch.setattr(
        sender_module, "send_calldata_transaction", mocked_sender
    )

    result = sender_module.send_verification_sequence(
        web3,
        CONTRACT,
        SENDER,
        verifier_address,
        submit_calldata,
        verify_calldata,
        agent_private_key="agent-test-key",
        verifier_private_key="verifier-test-key",
        expected_contract_address=CONTRACT,
    )

    assert not result.succeeded
    assert result.submit_result == failed_submit
    assert result.verify_result is None
    assert mocked_sender.call_count == 1


def _sequence_calldata(task_id):
    submit_selector = Web3.keccak(text="submitResult(uint256,bytes32)")[:4]
    verify_selector = Web3.keccak(text="verifyTask(uint256,bool,bytes32)")[:4]
    encoded_id = task_id.to_bytes(32, "big")
    submit = "0x" + (submit_selector + encoded_id + b"\x11" * 32).hex()
    verify = "0x" + (
        verify_selector + encoded_id + (1).to_bytes(32, "big") + b"\x22" * 32
    ).hex()
    return submit, verify


def _sequence_web3_with_test_keys():
    verifier_address = "0x0000000000000000000000000000000000000003"
    web3 = make_web3()
    agent_account = MagicMock()
    agent_account.address = SENDER
    verifier_account = MagicMock()
    verifier_account.address = verifier_address
    web3.eth.account.from_key.side_effect = lambda key: {
        "agent-test-key": agent_account,
        "verifier-test-key": verifier_account,
    }[key]
    return web3, verifier_address


def test_sequence_rejects_different_task_ids_before_sending(monkeypatch):
    import integration.transaction_sender as sender_module

    web3, verifier_address = _sequence_web3_with_test_keys()
    submit_calldata, _ = _sequence_calldata(7)
    _, verify_calldata = _sequence_calldata(8)
    mocked_sender = MagicMock()
    monkeypatch.setattr(
        sender_module, "send_calldata_transaction", mocked_sender
    )

    with pytest.raises(ValueError, match="different tasks"):
        sender_module.send_verification_sequence(
            web3, CONTRACT, SENDER, verifier_address,
            submit_calldata, verify_calldata,
            agent_private_key="agent-test-key",
            verifier_private_key="verifier-test-key",
            expected_contract_address=CONTRACT,
        )

    mocked_sender.assert_not_called()


def test_sequence_rejects_wrong_verifier_key_before_sending(monkeypatch):
    import integration.transaction_sender as sender_module

    web3, verifier_address = _sequence_web3_with_test_keys()
    submit_calldata, verify_calldata = _sequence_calldata(7)
    mocked_sender = MagicMock()
    monkeypatch.setattr(
        sender_module, "send_calldata_transaction", mocked_sender
    )

    with pytest.raises(ValueError, match="Verifier private key"):
        sender_module.send_verification_sequence(
            web3, CONTRACT, SENDER, verifier_address,
            submit_calldata, verify_calldata,
            agent_private_key="agent-test-key",
            verifier_private_key="agent-test-key",
            expected_contract_address=CONTRACT,
        )

    mocked_sender.assert_not_called()


def test_submit_only_is_not_reported_as_completed_sequence():
    import integration.transaction_sender as sender_module

    result = sender_module.VerificationSequenceResult(
        submit_result=sender_module.TransactionResult(
            "0x" + "44" * 32, 123, 42000, 1
        ),
        verify_result=None,
    )

    assert not result.succeeded
