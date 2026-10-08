from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
    VerificationStatus,
    VerificationScope,
    verify_erc20_observations,
)
from verifier.arbitrum_policy import ArbitrumERC20Policy
from verifier.canonical import sha256_hex


@dataclass(frozen=True)
class ArbitrumVerificationEvidence:
    chain_id: int
    policy_version: str
    scope: VerificationScope
    condition: ERC20TransferCondition
    observations: list[ERC20TransferObservation]
    status: VerificationStatus


@dataclass(frozen=True)
class ArbitrumVerificationResult:
    status: VerificationStatus
    evidence: ArbitrumVerificationEvidence
    evidence_hash: str


def verify_arbitrum_erc20(
    policy: ArbitrumERC20Policy,
    observations: list[ERC20TransferObservation],
    scope: VerificationScope,
) -> ArbitrumVerificationResult:
    if policy.policy_type != "arbitrum_erc20":
        raise ValueError(
            f"Unsupported policy type: {policy.policy_type}"
        )

    if scope.chain_id != policy.chain_id:
        raise ValueError(
            "Policy chain_id does not match verification scope chain_id"
        )

    status = verify_erc20_observations(
        condition=policy.to_condition(),
        observations=observations,
    )

    evidence = ArbitrumVerificationEvidence(
        chain_id=policy.chain_id,
        policy_version=policy.version,
        scope=scope,
        condition=policy.to_condition(),
        observations=observations,
        status=status,
    )

    return ArbitrumVerificationResult(
        status=status,
        evidence=evidence,
        evidence_hash=sha256_hex(asdict(evidence)),
    )
