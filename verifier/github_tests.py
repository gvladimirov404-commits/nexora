from __future__ import annotations

import requests

from verifier.github_checker import (
    check_github_repository,
    parse_github_repository,
)
from verifier.models import Evidence, Policy, VerificationResult


SUPPORTED_TEST_PROFILES = {
    "forge_test": {
        "workflow_file": "nexora-tests.yml",
    },
}


def check_github_tests(
    policy: Policy,
    evidence: Evidence,
    timeout: int = 10,
) -> VerificationResult:
    profile = SUPPORTED_TEST_PROFILES.get(policy.test_profile)

    if profile is None:
        raise ValueError(
            f"Unsupported test profile: {policy.test_profile}"
        )

    repository_result = check_github_repository(
        policy=policy,
        evidence=evidence,
        timeout=timeout,
    )

    if not repository_result.passed:
        return repository_result

    repository = parse_github_repository(evidence.repository_url)

    headers = {
        "Accept": "application/vnd.github+json",
    }

    workflow_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}/actions/workflows/"
        f"{profile['workflow_file']}"
    )

    workflow_response = requests.get(
        workflow_url,
        timeout=timeout,
        headers=headers,
    )

    if workflow_response.status_code != 200:
        return VerificationResult(
            repository_exists=repository_result.repository_exists,
            repository_public=repository_result.repository_public,
            required_files=repository_result.required_files,
            passed=False,
        )

    workflow_data = workflow_response.json()

    if workflow_data.get("path") != f".github/workflows/{profile['workflow_file']}":
        return VerificationResult(
            repository_exists=repository_result.repository_exists,
            repository_public=repository_result.repository_public,
            required_files=repository_result.required_files,
            passed=False,
        )

    workflow_id = workflow_data.get("id")

    if not workflow_id:
        return VerificationResult(
            repository_exists=repository_result.repository_exists,
            repository_public=repository_result.repository_public,
            required_files=repository_result.required_files,
            passed=False,
        )

    runs_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}/actions/workflows/"
        f"{workflow_id}/runs"
    )

    runs_response = requests.get(
        runs_url,
        params={
            "head_sha": evidence.commit_sha,
            "event": "push",
            "status": "completed",
        },
        timeout=timeout,
        headers=headers,
    )

    if runs_response.status_code != 200:
        return VerificationResult(
            repository_exists=repository_result.repository_exists,
            repository_public=repository_result.repository_public,
            required_files=repository_result.required_files,
            passed=False,
        )

    runs_data = runs_response.json()

    for run in runs_data.get("workflow_runs", []):
        if (
            run.get("head_sha") == evidence.commit_sha
            and run.get("event") == "push"
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
        ):
            return repository_result

    return VerificationResult(
        repository_exists=repository_result.repository_exists,
        repository_public=repository_result.repository_public,
        required_files=repository_result.required_files,
        passed=False,
    )
