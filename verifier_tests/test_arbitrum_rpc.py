from web3 import Web3

from verifier.arbitrum_erc20 import ERC20TransferCondition
from verifier.arbitrum_rpc import (
    TRANSFER_EVENT_TOPIC,
    observe_erc20_transfers,
)


TOKEN = "0x0000000000000000000000000000000000000001"
SENDER = "0x0000000000000000000000000000000000000002"
RECIPIENT = "0x0000000000000000000000000000000000000003"


def _address_topic(address: str) -> bytes:
    return bytes.fromhex(address[2:].rjust(64, "0"))


class FakeEth:
    def __init__(self, logs, block_timestamp=1000):
        self.logs = logs
        self.block_timestamp = block_timestamp

    def get_logs(self, params):
        assert params["address"] == Web3.to_checksum_address(TOKEN)
        assert params["topics"] == [TRANSFER_EVENT_TOPIC]
        assert params["fromBlock"] == 100
        assert params["toBlock"] == 200
        return self.logs

    def get_block(self, block_number):
        assert block_number == 150
        return {"timestamp": self.block_timestamp}


class FakeWeb3:
    def __init__(self, logs, block_timestamp=1000):
        self.eth = FakeEth(logs, block_timestamp)


def make_condition():
    return ERC20TransferCondition(
        token=TOKEN,
        sender=SENDER,
        recipient=RECIPIENT,
        minimum_amount=100,
        deadline=2000,
    )


def test_observer_decodes_transfer_log():
    log = {
        "topics": [
            bytes.fromhex(TRANSFER_EVENT_TOPIC[2:]),
            _address_topic(SENDER),
            _address_topic(RECIPIENT),
        ],
        "data": (100).to_bytes(32, "big"),
        "blockNumber": 150,
    }

    observations = observe_erc20_transfers(
        web3=FakeWeb3([log]),
        condition=make_condition(),
        from_block=100,
        to_block=200,
    )

    assert len(observations) == 1
    assert observations[0].token == Web3.to_checksum_address(TOKEN)
    assert observations[0].sender == Web3.to_checksum_address(SENDER)
    assert observations[0].recipient == Web3.to_checksum_address(RECIPIENT)
    assert observations[0].amount == 100
    assert observations[0].timestamp == 1000


def test_observer_returns_empty_list_when_no_logs():
    observations = observe_erc20_transfers(
        web3=FakeWeb3([]),
        condition=make_condition(),
        from_block=100,
        to_block=200,
    )

    assert observations == []


def test_observer_rejects_reversed_block_range():
    try:
        observe_erc20_transfers(
            web3=FakeWeb3([]),
            condition=make_condition(),
            from_block=200,
            to_block=100,
        )
    except ValueError as exc:
        assert str(exc) == "from_block must not be greater than to_block"
    else:
        raise AssertionError("Expected ValueError")
