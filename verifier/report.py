from __future__ import annotations

from dataclasses import dataclass

from verifier.canonical import (
    evidence_hash,
    policy_hash,
    verification_hash,
)
from verifier.engine import verify_task
from verifier.models import (
    Evidence,
    Policy,
    VerificationResult,
)


@dataclass(frozen=True)
class VerificationReport:
    policy_hash: str
    evidence_hash: str
    verification_hash: str
    result: VerificationResult


def create_verification_report(
    policy: Policy,
    evidence: Evidence,
) -> VerificationReport:
    result = verify_task(
        policy=policy,
        evidence=evidence,
    )

    return VerificationReport(
        policy_hash=policy_hash(policy),
        evidence_hash=evidence_hash(evidence),
        verification_hash=verification_hash(result),
        result=result,
    )
