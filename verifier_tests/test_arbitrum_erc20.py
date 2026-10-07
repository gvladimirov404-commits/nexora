from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
    VerificationStatus,
    verify_erc20_transfer,
)


TOKEN = "0x0000000000000000000000000000000000000001"
SENDER = "0x0000000000000000000000000000000000000002"
RECIPIENT = "0x0000000000000000000000000000000000000003"


def make_condition() -> ERC20TransferCondition:
    return ERC20TransferCondition(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        minimum_amount=100,
        deadline=1000,
    )


def test_matching_transfer_passes():
    observation = ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=100,
        timestamp=1000,
    )

    assert verify_erc20_transfer(make_condition(), observation) == VerificationStatus.PASS


def test_wrong_recipient_fails():
    observation = ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient="0x0000000000000000000000000000000000000004",
        amount=100,
        timestamp=1000,
    )

    assert verify_erc20_transfer(make_condition(), observation) == VerificationStatus.FAIL


def test_insufficient_amount_fails():
    observation = ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=99,
        timestamp=1000,
    )

    assert verify_erc20_transfer(make_condition(), observation) == VerificationStatus.FAIL


def test_transfer_after_deadline_fails():
    observation = ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=100,
        timestamp=1001,
    )

    assert verify_erc20_transfer(make_condition(), observation) == VerificationStatus.FAIL


def test_missing_observation_is_unknown():
    assert verify_erc20_transfer(make_condition(), None) == VerificationStatus.UNKNOWN


def test_missing_timestamp_is_unknown():
    observation = ERC20TransferObservation(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        amount=100,
        timestamp=None,
    )

    assert verify_erc20_transfer(make_condition(), observation) == VerificationStatus.UNKNOWN


def test_matching_observation_in_list_passes():
    condition = make_condition()

    observations = [
        ERC20TransferObservation(
            token=TOKEN,
            sender=SENDER,
            recipient=RECIPIENT,
            amount=150,
            timestamp=900,
        )
    ]

    from verifier.arbitrum_erc20 import verify_erc20_observations

    assert (
        verify_erc20_observations(condition, observations)
        == VerificationStatus.PASS
    )


def test_non_matching_observations_fail():
    condition = make_condition()

    observations = [
        ERC20TransferObservation(
            token=TOKEN,
            sender=SENDER,
            recipient="0x0000000000000000000000000000000000000004",
            amount=150,
            timestamp=900,
        )
    ]

    from verifier.arbitrum_erc20 import verify_erc20_observations

    assert (
        verify_erc20_observations(condition, observations)
        == VerificationStatus.FAIL
    )


def test_empty_observations_are_unknown():
    from verifier.arbitrum_erc20 import verify_erc20_observations

    assert (
        verify_erc20_observations(make_condition(), [])
        == VerificationStatus.UNKNOWN
    )


def test_matching_transfer_without_timestamp_is_unknown():
    condition = make_condition()

    observations = [
        ERC20TransferObservation(
            token=TOKEN,
            sender=SENDER,
            recipient=RECIPIENT,
            amount=150,
            timestamp=None,
        )
    ]

    from verifier.arbitrum_erc20 import verify_erc20_observations

    assert (
        verify_erc20_observations(condition, observations)
        == VerificationStatus.UNKNOWN
    )
