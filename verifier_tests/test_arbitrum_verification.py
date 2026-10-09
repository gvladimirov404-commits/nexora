from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
    VerificationStatus,
    VerificationScope,
)
from verifier.arbitrum_policy import ArbitrumERC20Policy
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


def make_policy(minimum_amount: int = 600) -> ArbitrumERC20Policy:
    return ArbitrumERC20Policy(
        version="1",
        chain_id=421614,
        condition=make_condition(minimum_amount=minimum_amount),
    )


def make_observation(amount: int = 600) -> ERC20TransferObservation:
    return ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=amount,
        timestamp=1000,
    )


def make_scope() -> VerificationScope:
    return VerificationScope(
        chain_id=421614,
        from_block=100,
        to_block=200,
    )


def test_matching_transfer_returns_pass_and_hash():
    result = verify_arbitrum_erc20(
        policy=make_policy(),
        observations=[make_observation()],
        scope=make_scope(),
    )

    assert result.status is VerificationStatus.PASS
    assert result.evidence.status is VerificationStatus.PASS
    assert result.evidence_hash


def test_insufficient_amount_returns_fail():
    result = verify_arbitrum_erc20(
        policy=make_policy(minimum_amount=601),
        observations=[make_observation()],
        scope=make_scope(),
    )

    assert result.status is VerificationStatus.FAIL
    assert result.evidence.status is VerificationStatus.FAIL


def test_no_observations_returns_unknown():
    result = verify_arbitrum_erc20(
        policy=make_policy(),
        observations=[],
        scope=make_scope(),
    )

    assert result.status is VerificationStatus.UNKNOWN
    assert result.evidence.status is VerificationStatus.UNKNOWN


def test_same_evidence_produces_same_hash():
    condition = make_condition()
    observations = [make_observation()]

    first = verify_arbitrum_erc20(
        policy=ArbitrumERC20Policy(
            version="1",
            chain_id=421614,
            condition=condition,
        ),
        observations=observations,
        scope=make_scope(),
    )
    second = verify_arbitrum_erc20(
        policy=ArbitrumERC20Policy(
            version="1",
            chain_id=421614,
            condition=condition,
        ),
        observations=observations,
        scope=make_scope(),
    )

    assert first.evidence_hash == second.evidence_hash


def test_changed_evidence_produces_different_hash():
    first = verify_arbitrum_erc20(
        policy=make_policy(),
        observations=[make_observation()],
        scope=make_scope(),
    )
    second = verify_arbitrum_erc20(
        policy=make_policy(minimum_amount=601),
        observations=[make_observation()],
        scope=make_scope(),
    )

    assert first.evidence_hash != second.evidence_hash


def test_changed_scope_produces_different_hash():
    first = verify_arbitrum_erc20(
        policy=make_policy(),
        observations=[make_observation()],
        scope=make_scope(),
    )
    second = verify_arbitrum_erc20(
        policy=make_policy(),
        observations=[make_observation()],
        scope=VerificationScope(
            chain_id=421614,
            from_block=101,
            to_block=200,
        ),
    )

    assert first.evidence_hash != second.evidence_hash


class WrongPolicyType:
    policy_type = "github_repository"

    def to_condition(self) -> ERC20TransferCondition:
        return make_condition()


def test_rejects_unsupported_policy_type():
    try:
        verify_arbitrum_erc20(
            policy=WrongPolicyType(),
            observations=[make_observation()],
            scope=make_scope(),
        )
    except ValueError as exc:
        assert str(exc) == "Unsupported policy type: github_repository"
    else:
        raise AssertionError("Expected ValueError")


def test_changed_policy_version_produces_different_hash():
    observations = [make_observation()]

    first = verify_arbitrum_erc20(
        policy=ArbitrumERC20Policy(
            version="1",
            chain_id=421614,
            condition=make_condition(),
        ),
        observations=observations,
        scope=make_scope(),
    )
    second = verify_arbitrum_erc20(
        policy=ArbitrumERC20Policy(
            version="2",
            chain_id=421614,
            condition=make_condition(),
        ),
        observations=observations,
        scope=make_scope(),
    )

    assert first.evidence_hash != second.evidence_hash

def test_rejects_mismatched_scope_chain_id():
    try:
        verify_arbitrum_erc20(
            policy=make_policy(),
            observations=[make_observation()],
            scope=VerificationScope(
                chain_id=1,
                from_block=100,
                to_block=200,
            ),
        )
    except ValueError as exc:
        assert str(exc) == "Policy chain_id does not match verification scope chain_id"
    else:
        raise AssertionError("Expected ValueError")

def test_later_valid_observation_overrides_earlier_failed_observation():
    result = verify_arbitrum_erc20(
        policy=make_policy(),
        observations=[
            make_observation(amount=599),
            make_observation(amount=600),
        ],
        scope=make_scope(),
    )

    assert result.status is VerificationStatus.PASS


def test_rejects_observation_outside_scope():
    observation = ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=600,
        timestamp=1000,
        block_number=201,
    )

    try:
        verify_arbitrum_erc20(
            policy=make_policy(),
            observations=[observation],
            scope=make_scope(),
        )
    except ValueError as exc:
        assert str(exc) == "Observation block_number outside verification scope"
    else:
        raise AssertionError("Expected ValueError")
