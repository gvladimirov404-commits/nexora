from __future__ import annotations

from verifier.github_checker import check_github_repository
from verifier.models import Evidence, Policy, VerificationResult


SUPPORTED_TASK_TYPES = {"github_repository"}


def verify_task(
    policy: Policy,
    evidence: Evidence,
) -> VerificationResult:
    if policy.task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(
            f"Unsupported task type: {policy.task_type}"
        )

    if policy.repository_visibility != "public":
        raise ValueError(
            "Only public GitHub repositories are supported"
        )

    return check_github_repository(
        policy=policy,
        evidence=evidence,
    )
