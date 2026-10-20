from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from verifier.models import Evidence, Policy, VerificationResult


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str


def parse_github_repository(url: str) -> GitHubRepository:
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError("GitHub URL must use HTTPS")

    if parsed.netloc.lower() != "github.com":
        raise ValueError("URL must point to github.com")

    parts = [part for part in parsed.path.split("/") if part]

    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL")

    return GitHubRepository(
        owner=parts[0],
        name=parts[1].removesuffix(".git"),
    )


def get_github_default_branch_commit(
    repository_url: str,
    timeout: int = 10,
) -> str:
    repository = parse_github_repository(repository_url)

    api_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}"
    )

    response = requests.get(
        api_url,
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
    )
    response.raise_for_status()

    repository_data = response.json()
    default_branch = repository_data["default_branch"]

    branch_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}/commits/"
        f"{default_branch}"
    )

    branch_response = requests.get(
        branch_url,
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
    )
    branch_response.raise_for_status()

    return branch_response.json()["sha"]


def _validate_required_files(required_files: list[str]) -> None:
    if not isinstance(required_files, list):
        raise ValueError("required_files must be a list of file paths")

    if not required_files:
        raise ValueError("Policy must list at least one required file")

    for name in required_files:
        if (
            not isinstance(name, str)
            or not name.strip()
            or any(char in name for char in "?#%\\")
            or any(part in {"", ".", ".."} for part in name.split("/"))
        ):
            raise ValueError(f"Invalid required file path: {name!r}")


def check_github_repository(
    policy: Policy,
    evidence: Evidence,
    timeout: int = 10,
) -> VerificationResult:
    _validate_required_files(policy.required_files)

    repository = parse_github_repository(evidence.repository_url)

    api_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}"
    )

    response = requests.get(
        api_url,
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
    )

    if response.status_code == 404:
        return VerificationResult(
            repository_exists=False,
            repository_public=False,
            required_files={
                filename: False
                for filename in policy.required_files
            },
            passed=False,
        )

    response.raise_for_status()

    repository_data = response.json()

    repository_exists = True
    repository_public = not repository_data.get("private", True)

    commit_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}/commits/"
        f"{evidence.commit_sha}"
    )

    commit_response = requests.get(
        commit_url,
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
    )

    if commit_response.status_code == 404:
        return VerificationResult(
            repository_exists=repository_exists,
            repository_public=repository_public,
            required_files={
                filename: False
                for filename in policy.required_files
            },
            passed=False,
        )

    commit_response.raise_for_status()
    if commit_response.status_code != 200:
        raise requests.HTTPError(
            f"Unexpected GitHub commit API status: "
            f"{commit_response.status_code}",
            response=commit_response,
        )

    commit_exists = True

    required_files: dict[str, bool] = {}

    for filename in policy.required_files:
        file_url = (
            f"https://api.github.com/repos/"
            f"{repository.owner}/{repository.name}/contents/{filename}"
            f"?ref={evidence.commit_sha}"
        )

        file_response = requests.get(
            file_url,
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )

        if file_response.status_code == 404:
            required_files[filename] = False
        else:
            file_response.raise_for_status()
            if file_response.status_code != 200:
                raise requests.HTTPError(
                    f"Unexpected GitHub file API status: "
                    f"{file_response.status_code}",
                    response=file_response,
                )
            required_files[filename] = True

    passed = (
        repository_exists
        and repository_public
        and commit_exists
        and all(required_files.values())
    )

    return VerificationResult(
        repository_exists=repository_exists,
        repository_public=repository_public,
        required_files=required_files,
        passed=passed,
    )
