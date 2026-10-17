"""Explicit transaction sender for NEXORA. Never broadcasts automatically."""

import os
from dataclasses import dataclass
from typing import Any

from web3 import Web3


ARBITRUM_SEPOLIA_CHAIN_ID = 421614


@dataclass(frozen=True)
class TransactionResult:
    tx_hash: str
    block_number: int
    gas_used: int
    status: int

    @property
    def succeeded(self) -> bool:
        return self.status == 1


@dataclass(frozen=True)
class VerificationSequenceResult:
    submit_result: TransactionResult
    verify_result: TransactionResult | None

    @property
    def succeeded(self) -> bool:
        """True only when both transactions completed successfully."""
        return (
            self.submit_result.succeeded
            and self.verify_result is not None
            and self.verify_result.succeeded
        )


def _normalize_hash(value: Any) -> str:
    if isinstance(value, bytes):
        result = "0x" + value.hex()
    elif hasattr(value, "hex"):
        result = value.hex()
    else:
        result = str(value)

    return result if result.startswith("0x") else "0x" + result


def _sequence_task_id(
    calldata: str, signature: str, argument_words: int, label: str
) -> int:
    if not isinstance(calldata, str) or not calldata.startswith("0x"):
        raise ValueError(f"{label} calldata must start with 0x")

    encoded = calldata[2:]
    if len(encoded) % 2:
        raise ValueError(f"{label} calldata has an odd number of hex characters")

    try:
        raw = bytes.fromhex(encoded)
    except ValueError as exc:
        raise ValueError(f"{label} calldata is not valid hexadecimal") from exc

    expected_length = 4 + 32 * argument_words
    if len(raw) != expected_length:
        raise ValueError(f"{label} calldata has an unexpected length")

    expected_selector = Web3.keccak(text=signature)[:4]
    if raw[:4] != expected_selector:
        raise ValueError(f"{label} calldata has the wrong function selector")

    return int.from_bytes(raw[4:36], "big")


def send_verification_sequence(
    web3: Any,
    contract_address: str,
    agent_address: str,
    verifier_address: str | None,
    submit_calldata: str,
    verify_calldata: str | None,
    *,
    agent_private_key: str,
    verifier_private_key: str | None,
    expected_contract_address: str,
    expected_chain_id: int = ARBITRUM_SEPOLIA_CHAIN_ID,
    receipt_timeout: int = 120,
) -> VerificationSequenceResult:
    """Send submitResult, then verifyTask only after a successful receipt.

    Both signing identities and all supplied calldata are checked before the
    first broadcast. Private keys are required explicitly and are not logged.
    A None verify_calldata means submit only, for example when verification
    has not produced a definitive PASS/FAIL decision.
    """
    if int(web3.eth.chain_id) != expected_chain_id:
        raise ValueError(
            f"Wrong network: expected chain {expected_chain_id}, "
            f"got {web3.eth.chain_id}"
        )

    target = Web3.to_checksum_address(contract_address)
    expected_target = Web3.to_checksum_address(expected_contract_address)
    if target != expected_target:
        raise ValueError(
            f"Wrong contract address: expected {expected_target}, got {target}"
        )

    submit_task_id = _sequence_task_id(
        submit_calldata, "submitResult(uint256,bytes32)", 2, "submitResult"
    )

    agent = Web3.to_checksum_address(agent_address)
    agent_account = web3.eth.account.from_key(agent_private_key)
    if Web3.to_checksum_address(agent_account.address) != agent:
        raise ValueError("Agent private key does not match agent address")

    verifier = None
    if verify_calldata is not None:
        if not verifier_address or not verifier_private_key:
            raise ValueError(
                "Verifier address and private key are required for verifyTask"
            )

        verify_task_id = _sequence_task_id(
            verify_calldata,
            "verifyTask(uint256,bool,bytes32)",
            3,
            "verifyTask",
        )
        if verify_task_id != submit_task_id:
            raise ValueError(
                "submitResult and verifyTask calldata refer to different tasks"
            )

        verifier = Web3.to_checksum_address(verifier_address)
        verifier_account = web3.eth.account.from_key(verifier_private_key)
        if Web3.to_checksum_address(verifier_account.address) != verifier:
            raise ValueError(
                "Verifier private key does not match verifier address"
            )

    submit_result = send_calldata_transaction(
        web3,
        target,
        agent,
        submit_calldata,
        private_key=agent_private_key,
        expected_chain_id=expected_chain_id,
        expected_contract_address=expected_target,
        receipt_timeout=receipt_timeout,
    )

    if not submit_result.succeeded or verify_calldata is None:
        return VerificationSequenceResult(submit_result, None)

    verify_result = send_calldata_transaction(
        web3,
        target,
        verifier,
        verify_calldata,
        private_key=verifier_private_key,
        expected_chain_id=expected_chain_id,
        expected_contract_address=expected_target,
        receipt_timeout=receipt_timeout,
    )
    return VerificationSequenceResult(submit_result, verify_result)


def send_calldata_transaction(
    web3: Any,
    contract_address: str,
    sender_address: str,
    calldata: str,
    *,
    value: int = 0,
    private_key: str | None = None,
    expected_chain_id: int = ARBITRUM_SEPOLIA_CHAIN_ID,
    expected_contract_address: str | None = None,
    receipt_timeout: int = 120,
) -> TransactionResult:
    """Sign, broadcast, and await one explicitly requested transaction.

    If private_key is omitted, NEXORA_PRIVATE_KEY is read from the environment.
    The key is never printed or written to disk by this module.
    """

    if value < 0:
        raise ValueError("value must not be negative")

    if not isinstance(calldata, str) or not calldata.startswith("0x"):
        raise ValueError("calldata must be a 0x-prefixed hex string")

    try:
        data = bytes.fromhex(calldata[2:])
    except ValueError as exc:
        raise ValueError("calldata contains invalid hexadecimal data") from exc

    if len(calldata[2:]) % 2:
        raise ValueError("calldata must contain pairs of hexadecimal digits")

    actual_chain_id = int(web3.eth.chain_id)
    if actual_chain_id != expected_chain_id:
        raise ValueError(
            f"Wrong network: expected chain ID {expected_chain_id}, "
            f"got {actual_chain_id}"
        )

    key = private_key or os.environ.get("NEXORA_PRIVATE_KEY")
    if not key:
        raise ValueError(
            "Set NEXORA_PRIVATE_KEY in the environment before sending"
        )

    account = web3.eth.account.from_key(key)
    sender = Web3.to_checksum_address(sender_address)
    if Web3.to_checksum_address(account.address) != sender:
        raise ValueError("Private key does not match sender_address")

    target = Web3.to_checksum_address(contract_address)
    if expected_contract_address is not None:
        expected_target = Web3.to_checksum_address(expected_contract_address)
        if target != expected_target:
            raise ValueError(
                f"Wrong contract address: expected {expected_target}, got {target}"
            )

    nonce = web3.eth.get_transaction_count(sender, "pending")

    estimate = int(
        web3.eth.estimate_gas(
            {
                "from": sender,
                "to": target,
                "data": data,
                "value": value,
            }
        )
    )
    gas_limit = max(estimate + 10_000, (estimate * 120 + 99) // 100)

    transaction = {
        "chainId": actual_chain_id,
        "from": sender,
        "to": target,
        "nonce": nonce,
        "value": value,
        "data": data,
        "gas": gas_limit,
        "gasPrice": int(web3.eth.gas_price),
    }

    signed = web3.eth.account.sign_transaction(transaction, key)
    raw_transaction = getattr(signed, "raw_transaction", None)
    if raw_transaction is None:
        raw_transaction = signed.rawTransaction

    tx_hash = web3.eth.send_raw_transaction(raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(
        tx_hash, timeout=receipt_timeout
    )

    return TransactionResult(
        tx_hash=_normalize_hash(tx_hash),
        block_number=int(receipt["blockNumber"]),
        gas_used=int(receipt["gasUsed"]),
        status=int(receipt["status"]),
    )
