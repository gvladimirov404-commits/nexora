from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from verifier.arbitrum_erc20 import (
    ERC20TransferCondition,
    ERC20TransferObservation,
    VerificationStatus,
    verify_erc20_observations,
)
from verifier.canonical import sha256_hex


@dataclass(frozen=True)
class ArbitrumVerificationEvidence:
    chain_id: int
    condition: ERC20TransferCondition
    observations: list[ERC20TransferObservation]
    status: VerificationStatus


@dataclass(frozen=True)
class ArbitrumVerificationResult:
    status: VerificationStatus
    evidence: ArbitrumVerificationEvidence
    evidence_hash: str


def verify_arbitrum_erc20(
    chain_id: int,
    condition: ERC20TransferCondition,
    observations: list[ERC20TransferObservation],
) -> ArbitrumVerificationResult:
    status = verify_erc20_observations(
        condition=condition,
        observations=observations,
    )

    evidence = ArbitrumVerificationEvidence(
        chain_id=chain_id,
        condition=condition,
        observations=observations,
        status=status,
    )

    return ArbitrumVerificationResult(
        status=status,
        evidence=evidence,
        evidence_hash=sha256_hex(asdict(evidence)),
    )
