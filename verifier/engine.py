from __future__ import annotations

from verifier.github_checker import check_github_repository
from verifier.github_tests import check_github_tests
from verifier.models import Evidence, Policy, VerificationResult
from verifier.registry import UniversalVerificationResult, Verifier, VerifierRegistry
from verifier.canonical import evidence_hash, policy_hash, verification_hash
from verifier.report_checker import verify_report


def _adapt_github_result(policy: Policy, evidence: Evidence, checker):
    result = checker(policy=policy, evidence=evidence)
    return UniversalVerificationResult(
        status="PASS" if result.passed else "FAIL",
        policy_hash=policy_hash(policy),
        evidence_hash=evidence_hash(evidence),
        verification_hash=verification_hash(result),
        details={
            "task_type": policy.task_type,
            "repository_exists": result.repository_exists,
            "repository_public": result.repository_public,
            "required_files": result.required_files,
            "passed": result.passed,
        },
    )


def _verify_github_repository(policy: Policy, evidence: Evidence):
    return _adapt_github_result(policy, evidence, check_github_repository)


def _verify_github_tests(policy: Policy, evidence: Evidence):
    return _adapt_github_result(policy, evidence, check_github_tests)


_REGISTRY = VerifierRegistry()
_REGISTRY.register("github_repository", _verify_github_repository)
_REGISTRY.register("github_tests", _verify_github_tests)
_REGISTRY.register("report", verify_report)

SUPPORTED_TASK_TYPES = {"github_repository", "github_tests"}


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

    if policy.repository_url != evidence.repository_url:
        raise ValueError(
            "Policy repository does not match evidence repository"
        )

    universal_result = _REGISTRY.verify(
        policy.task_type,
        policy,
        evidence,
    )

    # Preserve the legacy public API and result model.
    details = universal_result.details
    return VerificationResult(
        repository_exists=details["repository_exists"],
        repository_public=details["repository_public"],
        required_files=details["required_files"],
        passed=universal_result.status == "PASS",
    )


def is_task_type_registered(task_type: str) -> bool:
    """Return whether the engine has a verifier for this task type."""
    return _REGISTRY.supports(task_type)


def verify_registered_task(
    policy,
    evidence,
) -> UniversalVerificationResult:
    """Verify a task through the registry without GitHub-specific checks."""
    return _REGISTRY.verify(
        policy.task_type,
        policy,
        evidence,
    )



def register_task_verifier(task_type: str, verifier: Verifier) -> None:
    """Register a verifier through the public engine interface."""
    _REGISTRY.register(task_type, verifier)
