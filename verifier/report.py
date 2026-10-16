from __future__ import annotations

from dataclasses import asdict, dataclass

from verifier.canonical import (
    evidence_hash as input_evidence_hash,
    policy_hash,
    sha256_hex,
)
from verifier.engine import verify_task
from verifier.models import Evidence, Policy, VerificationResult


@dataclass(frozen=True)
class VerificationReport:
    policy_hash: str
    result_hash: str
    evidence_hash: str
    verification_hash: str
    result: VerificationResult


def create_verification_report(
    policy: Policy,
    evidence: Evidence,
) -> VerificationReport:
    result = verify_task(policy=policy, evidence=evidence)
    policy_digest = policy_hash(policy)
    result_digest = input_evidence_hash(evidence)

    audit_package = {
        "schema": "nexora.audit.v1",
        "policy_hash": policy_digest,
        "result_hash": result_digest,
        "verification_result": asdict(result),
        "passed": result.passed,
    }
    audit_digest = sha256_hex(audit_package)
    decision_digest = sha256_hex({
        "schema": "nexora.decision.v1",
        "policy_hash": policy_digest,
        "result_hash": result_digest,
        "evidence_hash": audit_digest,
        "passed": result.passed,
    })

    return VerificationReport(
        policy_hash=policy_digest,
        result_hash=result_digest,
        evidence_hash=audit_digest,
        verification_hash=decision_digest,
        result=result,
    )
