from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
    VerificationStatus,
)
from verifier.arbitrum_verification import verify_arbitrum_erc20


TOKEN = "0x9b3541C7ABF9Aa3acD990b3547F64ff476f91DA2"
SENDER = "0x25011a401e7c67699D098f02bc8A2385fd618232"
RECIPIENT = "0x43515aef2d9dd9cadfd3cc4f3282c371ad910684"


def make_condition(minimum_amount: int = 600) -> ERC20TransferCondition:
    return ERC20TransferCondition(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        minimum_amount=minimum_amount,
        deadline=1000,
    )


def make_observation(amount: int = 600) -> ERC20TransferObservation:
    return ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=amount,
        timestamp=1000,
    )


def test_matching_transfer_returns_pass_and_hash():
    result = verify_arbitrum_erc20(
        chain_id=421614,
        condition=make_condition(),
        observations=[make_observation()],
    )

    assert result.status is VerificationStatus.PASS
    assert result.evidence.status is VerificationStatus.PASS
    assert result.evidence_hash


def test_insufficient_amount_returns_fail():
    result = verify_arbitrum_erc20(
        chain_id=421614,
        condition=make_condition(minimum_amount=601),
        observations=[make_observation()],
    )

    assert result.status is VerificationStatus.FAIL
    assert result.evidence.status is VerificationStatus.FAIL


def test_no_observations_returns_unknown():
    result = verify_arbitrum_erc20(
        chain_id=421614,
        condition=make_condition(),
        observations=[],
    )

    assert result.status is VerificationStatus.UNKNOWN
    assert result.evidence.status is VerificationStatus.UNKNOWN


def test_same_evidence_produces_same_hash():
    condition = make_condition()
    observations = [make_observation()]

    first = verify_arbitrum_erc20(
        chain_id=421614,
        condition=condition,
        observations=observations,
    )
    second = verify_arbitrum_erc20(
        chain_id=421614,
        condition=condition,
        observations=observations,
    )

    assert first.evidence_hash == second.evidence_hash


def test_changed_evidence_produces_different_hash():
    first = verify_arbitrum_erc20(
        chain_id=421614,
        condition=make_condition(),
        observations=[make_observation()],
    )
    second = verify_arbitrum_erc20(
        chain_id=421614,
        condition=make_condition(minimum_amount=601),
        observations=[make_observation()],
    )

    assert first.evidence_hash != second.evidence_hash
