from unittest.mock import Mock, patch

from verifier.github_checker import check_github_repository
from verifier.models import Evidence, Policy


def make_policy():
    return Policy(
        version="1.0",
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
