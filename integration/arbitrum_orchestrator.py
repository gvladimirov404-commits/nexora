from __future__ import annotations

from dataclasses import dataclass

from web3 import Web3

from integration.transactions import encode_submit_result, encode_verify_task
from verifier.arbitrum_erc20 import (
    ERC20TransferObservation,
    VerificationScope,
    VerificationStatus,
)
from verifier.arbitrum_policy import ArbitrumERC20Policy
from verifier.arbitrum_rpc import observe_erc20_transfers
from verifier.arbitrum_verification import (
    ArbitrumVerificationResult,
    verify_arbitrum_erc20,
)


@dataclass(frozen=True)
class ArbitrumVerificationPreparation:
    result: ArbitrumVerificationResult
    submit_calldata: str
    verify_calldata: str | None


def prepare_arbitrum_verification(
    web3: Web3,
    contract_address: str,
    task_id: int,
    policy: ArbitrumERC20Policy,
    observations: list[ERC20TransferObservation],
    scope: VerificationScope,
) -> ArbitrumVerificationPreparation:
    result = verify_arbitrum_erc20(
        policy=policy,
        observations=observations,
        scope=scope,
    )

    submit_calldata = encode_submit_result(
        web3=web3,
        contract_address=contract_address,
        task_id=task_id,
        result_hash=result.evidence_hash,
    )

    verify_calldata: str | None = None

    if result.status in {
        VerificationStatus.PASS,
        VerificationStatus.FAIL,
    }:
        verify_calldata = encode_verify_task(
            web3=web3,
            contract_address=contract_address,
            task_id=task_id,
            passed=result.status is VerificationStatus.PASS,
            evidence_hash=result.evidence_hash,
        )

    return ArbitrumVerificationPreparation(
        result=result,
        submit_calldata=submit_calldata,
        verify_calldata=verify_calldata,
    )


def prepare_arbitrum_verification_from_rpc(
    web3: Web3,
    contract_address: str,
    task_id: int,
    policy: ArbitrumERC20Policy,
    from_block: int,
    to_block: int,
) -> ArbitrumVerificationPreparation:
    observed = observe_erc20_transfers(
        web3=web3,
        condition=policy.to_condition(),
        from_block=from_block,
        to_block=to_block,
    )
    return prepare_arbitrum_verification(
        web3=web3,
        contract_address=contract_address,
        task_id=task_id,
        policy=policy,
        observations=observed.observations,
        scope=observed.scope,
    )
