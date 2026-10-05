from unittest.mock import Mock, patch

from verifier.github_tests import check_github_tests
from verifier.models import Evidence, Policy


def make_policy():
    return Policy(
        version="1.0",
        repository_url="https://github.com/example/project",
        task_type="github_tests",
        repository_visibility="public",
        required_files=["README.md", "LICENSE"],
        test_profile="forge_test",
    )


def make_evidence():
    return Evidence(
        repository_url="https://github.com/example/project",
        commit_sha="abc123",
    )


def repository_responses():
    repository_response = Mock()
    repository_response.status_code = 200
    repository_response.json.return_value = {"private": False}

    commit_response = Mock()
    commit_response.status_code = 200

    readme_response = Mock()
    readme_response.status_code = 200

    license_response = Mock()
    license_response.status_code = 200

    return [
        repository_response,
        commit_response,
        readme_response,
        license_response,
    ]


@patch("verifier.github_tests.requests.get")
def test_github_tests_passes_with_successful_push_run(mock_get):
    mock_get.side_effect = [
        *repository_responses(),
        Mock(
            status_code=200,
            json=lambda: {
                "id": 123,
                "path": ".github/workflows/nexora-tests.yml",
            },
        ),
        Mock(
            status_code=200,
            json=lambda: {
                "workflow_runs": [
                    {
                        "id": 456,
                        "head_sha": "abc123",
                        "event": "push",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            },
        ),
    ]

    result = check_github_tests(make_policy(), make_evidence())

    assert result.passed is True


@patch("verifier.github_tests.requests.get")
def test_github_tests_fails_when_run_is_for_different_commit(mock_get):
    mock_get.side_effect = [
        *repository_responses(),
        Mock(
            status_code=200,
            json=lambda: {
                "id": 123,
                "path": ".github/workflows/nexora-tests.yml",
            },
        ),
        Mock(
            status_code=200,
            json=lambda: {
                "workflow_runs": [
                    {
                        "id": 456,
                        "head_sha": "different",
                        "event": "push",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            },
        ),
    ]

    result = check_github_tests(make_policy(), make_evidence())

    assert result.passed is False


@patch("verifier.github_tests.requests.get")
def test_github_tests_fails_when_run_is_not_successful(mock_get):
    mock_get.side_effect = [
        *repository_responses(),
        Mock(
            status_code=200,
            json=lambda: {
                "id": 123,
                "path": ".github/workflows/nexora-tests.yml",
            },
        ),
        Mock(
            status_code=200,
            json=lambda: {
                "workflow_runs": [
                    {
                        "id": 456,
                        "head_sha": "abc123",
                        "event": "push",
                        "status": "completed",
                        "conclusion": "failure",
                    }
                ]
            },
        ),
    ]

    result = check_github_tests(make_policy(), make_evidence())

    assert result.passed is False


@patch("verifier.github_tests.requests.get")
def test_github_tests_fails_when_run_is_pull_request(mock_get):
    mock_get.side_effect = [
        *repository_responses(),
        Mock(
            status_code=200,
            json=lambda: {
                "id": 123,
                "path": ".github/workflows/nexora-tests.yml",
            },
        ),
        Mock(
            status_code=200,
            json=lambda: {
                "workflow_runs": [
                    {
                        "id": 456,
                        "head_sha": "abc123",
                        "event": "pull_request",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ]
            },
        ),
    ]

    result = check_github_tests(make_policy(), make_evidence())

    assert result.passed is False
