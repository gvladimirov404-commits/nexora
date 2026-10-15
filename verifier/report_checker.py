from __future__ import annotations
from dataclasses import dataclass

from typing import Any

from verifier.canonical import (
    evidence_hash,
    policy_hash,
    verification_hash,
)
from verifier.registry import UniversalVerificationResult


@dataclass(frozen=True)
class ReportVerificationPayload:
    status: str
    sections: dict[str, bool]


def verify_report(
    policy: Any,
    evidence: Any,
) -> UniversalVerificationResult:
    content = getattr(evidence, "content", None)
    required_sections = getattr(policy, "required_sections", None)

    if not isinstance(content, str):
        content = ""

    if not isinstance(required_sections, (list, tuple)):
        required_sections = ()

    normalized_content = content.casefold()

    section_results = {
        section: (
            isinstance(section, str)
            and bool(section.strip())
            and section.casefold() in normalized_content
        )
        for section in required_sections
    }

    passed = (
        bool(content.strip())
        and bool(section_results)
        and all(section_results.values())
    )

    result_data = {
        "status": "PASS" if passed else "FAIL",
        "sections": section_results,
    }

    return UniversalVerificationResult(
        status=result_data["status"],
        policy_hash=policy_hash(policy),
        evidence_hash=evidence_hash(evidence),
        verification_hash=verification_hash(
            ReportVerificationPayload(
                status=result_data["status"],
                sections=section_results,
            )
        ),
        details={
            "task_type": "report",
            "required_sections": section_results,
            "passed": passed,
        },
    )
