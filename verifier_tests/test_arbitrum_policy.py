from verifier.arbitrum_erc20 import ERC20TransferCondition
from verifier.arbitrum_policy import ArbitrumERC20Policy


def make_condition() -> ERC20TransferCondition:
    return ERC20TransferCondition(
        token="0x0000000000000000000000000000000000000001",
        sender="0x0000000000000000000000000000000000000002",
        recipient="0x0000000000000000000000000000000000000003",
        minimum_amount=600,
        deadline=1000,
    )


def test_policy_preserves_version_and_chain():
    policy = ArbitrumERC20Policy(
        version="1",
        chain_id=421614,
        condition=make_condition(),
    )

    assert policy.version == "1"
    assert policy.chain_id == 421614


def test_policy_converts_to_condition():
    condition = make_condition()
    policy = ArbitrumERC20Policy(
        version="1",
        chain_id=421614,
        condition=condition,
    )

    assert policy.to_condition() == condition
