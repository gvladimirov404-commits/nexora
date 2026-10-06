from __future__ import annotations

from dataclasses import dataclass

from web3 import Web3

from integration.transactions import encode_submit_result, encode_verify_task
from verifier.models import Evidence, Policy
from verifier.report import VerificationReport, create_verification_report


@dataclass(frozen=True)
class VerificationPreparation:
    report: VerificationReport
    submit_calldata: str
    verify_calldata: str


def prepare_verification(
    web3: Web3,
    contract_address: str,
    task_id: int,
    policy: Policy,
    evidence: Evidence,
) -> VerificationPreparation:
    report = create_verification_report(
        policy=policy,
        evidence=evidence,
    )

    submit_calldata = encode_submit_result(
        web3=web3,
        contract_address=contract_address,
        task_id=task_id,
        result_hash=report.evidence_hash,
    )

    verify_calldata = encode_verify_task(
        web3=web3,
        contract_address=contract_address,
        task_id=task_id,
        passed=report.result.passed,
        evidence_hash=report.evidence_hash,
    )

    return VerificationPreparation(
        report=report,
        submit_calldata=submit_calldata,
        verify_calldata=verify_calldata,
    )
