from web3 import Web3

from integration.arbitrum_orchestrator import prepare_arbitrum_verification
from integration.contract import create_contract
from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
    VerificationStatus,
)


TOKEN = "0x9b3541C7ABF9Aa3acD990b3547F64ff476f91DA2"
SENDER = "0x25011a401e7c67699D098f02bc8A2385fd618232"
RECIPIENT = "0x43515aef2d9dd9cadfd3cc4f3282c371ad910684"


def make_condition(minimum_amount: int = 600):
    return ERC20TransferCondition(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        minimum_amount=minimum_amount,
        deadline=1000,
    )


def make_observation(amount: int = 600):
    return ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=amount,
        timestamp=1000,
    )


def test_pass_prepares_submit_and_verify():
    web3 = Web3()
    result = prepare_arbitrum_verification(
        web3=web3,
        contract_address="0x0000000000000000000000000000000000000001",
        task_id=7,
        chain_id=421614,
        condition=make_condition(),
        observations=[make_observation()],
    )

    assert result.result.status is VerificationStatus.PASS
    assert result.submit_calldata.startswith("0x")
    assert result.verify_calldata is not None

    contract = create_contract(
        web3,
        "0x0000000000000000000000000000000000000001",
    )

    _, submit_args = contract.decode_function_input(result.submit_calldata)
    assert submit_args["taskId"] == 7
    assert submit_args["resultHash"].hex() == result.result.evidence_hash

    _, verify_args = contract.decode_function_input(result.verify_calldata)
    assert verify_args["taskId"] == 7
    assert verify_args["passed"] is True
    assert verify_args["evidenceHash"].hex() == result.result.evidence_hash


def test_fail_prepares_submit_and_failed_verify():
    web3 = Web3()
    result = prepare_arbitrum_verification(
        web3=web3,
        contract_address="0x0000000000000000000000000000000000000001",
        task_id=8,
        chain_id=421614,
        condition=make_condition(minimum_amount=601),
        observations=[make_observation()],
    )

    assert result.result.status is VerificationStatus.FAIL
    assert result.submit_calldata.startswith("0x")
    assert result.verify_calldata is not None

    contract = create_contract(
        web3,
        "0x0000000000000000000000000000000000000001",
    )

    _, verify_args = contract.decode_function_input(result.verify_calldata)
    assert verify_args["taskId"] == 8
    assert verify_args["passed"] is False
    assert verify_args["evidenceHash"].hex() == result.result.evidence_hash


def test_unknown_does_not_prepare_verify_calldata():
    web3 = Web3()
    result = prepare_arbitrum_verification(
        web3=web3,
        contract_address="0x0000000000000000000000000000000000000001",
        task_id=9,
        chain_id=421614,
        condition=make_condition(),
        observations=[],
    )

    assert result.result.status is VerificationStatus.UNKNOWN
    assert result.submit_calldata.startswith("0x")
    assert result.verify_calldata is None
