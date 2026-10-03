from __future__ import annotations

from web3 import Web3


def hex_to_bytes32(value: str) -> bytes:
    if not isinstance(value, str):
        raise TypeError("Hash must be a string")

    if value.startswith("0x"):
        value = value[2:]

    if len(value) != 64:
        raise ValueError("Hash must contain exactly 32 bytes")

    try:
        return Web3.to_bytes(hexstr="0x" + value)
    except ValueError as exc:
        raise ValueError("Hash must be valid hexadecimal") from exc
