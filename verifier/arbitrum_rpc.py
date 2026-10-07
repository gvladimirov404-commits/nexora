from __future__ import annotations

from web3 import Web3

from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
)


TRANSFER_EVENT_TOPIC = "0x" + Web3.keccak(
    text="Transfer(address,address,uint256)"
).hex()


def _topic_address(topic: bytes | str) -> str:
    value = topic.hex() if isinstance(topic, bytes) else topic
    return Web3.to_checksum_address("0x" + value[-40:])


def observe_erc20_transfers(
    web3: Web3,
    condition: ERC20TransferCondition,
    from_block: int,
    to_block: int,
) -> list[ERC20TransferObservation]:
    if from_block > to_block:
        raise ValueError("from_block must not be greater than to_block")

    logs = web3.eth.get_logs(
        {
            "address": Web3.to_checksum_address(condition.token),
            "topics": [TRANSFER_EVENT_TOPIC],
            "fromBlock": from_block,
            "toBlock": to_block,
        }
    )

    observations: list[ERC20TransferObservation] = []

    for log in logs:
        if len(log["topics"]) < 3:
            continue

        sender = _topic_address(log["topics"][1])
        recipient = _topic_address(log["topics"][2])

        amount = int(log["data"].hex(), 16)

        block = web3.eth.get_block(log["blockNumber"])

        observations.append(
            ERC20TransferObservation(
                token=Web3.to_checksum_address(condition.token),
                sender=sender,
                recipient=recipient,
                amount=amount,
                timestamp=block["timestamp"],
            )
        )

    return observations
