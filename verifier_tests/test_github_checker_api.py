from unittest.mock import Mock, patch

import pytest
import requests

from verifier.github_checker import check_github_repository
from verifier.models import Evidence, Policy


def make_policy():
    return Policy(
        version="1.0",
        repository_url="https://github.com/example/project",
        task_type="github_repository",
        repository_visibility="public",
        required_files=["README.md", "LICENSE"],
    )


def make_evidence():
    return Evidence(
        repository_url="https://github.com/example/project",
        commit_sha="abc123",
    )


@patch("verifier.github_checker.requests.get")
def test_github_repository_passes(mock_get):
    repository_response = Mock()
    repository_response.status_code = 200
    repository_response.json.return_value = {"private": False}

    readme_response = Mock()
    readme_response.status_code = 200

    license_response = Mock()
    license_response.status_code = 200

    commit_response = Mock()
    commit_response.status_code = 200

    mock_get.side_effect = [
        repository_response,
        commit_response,
        readme_response,
        license_response,
    ]

    result = check_github_repository(
        make_policy(),
        make_evidence(),
    )

    assert result.repository_exists is True
    assert result.repository_public is True
    assert result.required_files["README.md"] is True
    assert result.required_files["LICENSE"] is True
    assert result.passed is True


@patch("verifier.github_checker.requests.get")
def test_github_repository_fails_when_file_missing(mock_get):
    repository_response = Mock()
    repository_response.status_code = 200
    repository_response.json.return_value = {"private": False}

    readme_response = Mock()
    readme_response.status_code = 200

    license_response = Mock()
    license_response.status_code = 404

    commit_response = Mock()
    commit_response.status_code = 200

    mock_get.side_effect = [
        repository_response,
        commit_response,
        readme_response,
        license_response,
    ]

    result = check_github_repository(
        make_policy(),
        make_evidence(),
    )

    assert result.repository_exists is True
    assert result.repository_public is True
    assert result.required_files["README.md"] is True
    assert result.required_files["LICENSE"] is False
    assert result.passed is False


@patch("verifier.github_checker.requests.get")
def test_github_repository_fails_when_repository_not_found(mock_get):
    repository_response = Mock()
    repository_response.status_code = 404

    mock_get.return_value = repository_response

    result = check_github_repository(
        make_policy(),
        make_evidence(),
    )

    assert result.repository_exists is False
    assert result.repository_public is False
    assert result.required_files["README.md"] is False
    assert result.required_files["LICENSE"] is False
    assert result.passed is False


@patch("verifier.github_checker.requests.get")
def test_github_repository_checks_files_at_evidence_commit(mock_get):
    repository_response = Mock()
    repository_response.status_code = 200
    repository_response.json.return_value = {"private": False}

    commit_response = Mock()
    commit_response.status_code = 200

    readme_response = Mock()
    readme_response.status_code = 200

    license_response = Mock()
    license_response.status_code = 200

    mock_get.side_effect = [
        repository_response,
        commit_response,
        readme_response,
        license_response,
    ]

    result = check_github_repository(
        make_policy(),
        make_evidence(),
    )

    assert result.passed is True

    calls = mock_get.call_args_list

    assert "?ref=abc123" in calls[2].args[0]
    assert "?ref=abc123" in calls[3].args[0]


def test_get_github_default_branch_commit():
    from verifier.github_checker import get_github_default_branch_commit

    responses = [
        {
            "default_branch": "main",
        },
        {
            "sha": "abc123",
        },
    ]

    with patch("verifier.github_checker.requests.get") as mock_get:
        mock_get.side_effect = [
            type(
                "Response",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: responses[0],
                },
            )(),
            type(
                "Response",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: responses[1],
                },
            )(),
        ]

        sha = get_github_default_branch_commit(
            "https://github.com/example/project"
        )

    assert sha == "abc123"
    assert mock_get.call_count == 2

@pytest.mark.parametrize("status_code", [403, 429])
@pytest.mark.parametrize("stage", ["commit", "file"])
def test_github_api_errors_are_not_reported_as_missing_resources(
    status_code, stage
):
    repository_response = Mock()
    repository_response.status_code = 200
    repository_response.json.return_value = {"private": False}

    commit_response = Mock()
    commit_response.status_code = 200

    error_response = Mock()
    error_response.status_code = status_code
    error_response.raise_for_status.side_effect = requests.HTTPError(
        f"HTTP {status_code}", response=error_response
    )

    if stage == "commit":
        responses = [repository_response, error_response]
    else:
        responses = [
            repository_response,
            commit_response,
            error_response,
        ]

    with patch(
        "verifier.github_checker.requests.get",
        side_effect=responses,
    ):
        with pytest.raises(requests.HTTPError):
            check_github_repository(make_policy(), make_evidence())


def make_policy_with(required_files):
    from dataclasses import replace

    return replace(make_policy(), required_files=required_files)


def test_empty_required_files_is_rejected_before_any_request():
    with patch("verifier.github_checker.requests.get") as mock_get:
        with pytest.raises(ValueError, match="at least one required file"):
            check_github_repository(make_policy_with([]), make_evidence())

    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "required_files",
    [None, "README.md", (), ("README.md",)],
)
def test_non_list_required_files_is_rejected_before_any_request(required_files):
    with patch("verifier.github_checker.requests.get") as mock_get:
        with pytest.raises(ValueError, match="must be a list"):
            check_github_repository(
                make_policy_with(required_files),
                make_evidence(),
            )

    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "bad_name",
    [
        "",
        "   ",
        ".",
        "..",
        "a/../b",
        "/README.md",
        "docs/",
        "a//b",
        "README.md?ref=x",
        "README.md#",
        "100%.md",
        "%2e%2e/branches/main",
        "..\\branches\\main",
        5,
    ],
)
def test_invalid_required_file_paths_are_rejected_before_any_request(bad_name):
    with patch("verifier.github_checker.requests.get") as mock_get:
        with pytest.raises(ValueError, match="Invalid required file path"):
            check_github_repository(
                make_policy_with(["README.md", bad_name]),
                make_evidence(),
            )

    mock_get.assert_not_called()


def test_nested_required_file_paths_are_requested_at_the_evidence_commit():
    repository_response = Mock(status_code=200)
    repository_response.json.return_value = {"private": False}

    with patch("verifier.github_checker.requests.get") as mock_get:
        mock_get.side_effect = [
            repository_response,
            Mock(status_code=200),
            Mock(status_code=200),
            Mock(status_code=200),
        ]
        result = check_github_repository(
            make_policy_with(["docs/README.md", ".github/workflows/ci.yml"]),
            make_evidence(),
        )

    requested_urls = [call.args[0] for call in mock_get.call_args_list]
    assert requested_urls == [
        "https://api.github.com/repos/example/project",
        "https://api.github.com/repos/example/project/commits/abc123",
        "https://api.github.com/repos/example/project/contents/docs/README.md?ref=abc123",
        "https://api.github.com/repos/example/project/contents/.github/workflows/ci.yml?ref=abc123",
    ]
    assert result.required_files == {
        "docs/README.md": True,
        ".github/workflows/ci.yml": True,
    }
    assert result.passed is True
