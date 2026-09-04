import pytest

from verifier.github_checker import parse_github_repository


def test_parse_github_repository():
    repository = parse_github_repository(
        "https://github.com/example/project"
    )

    assert repository.owner == "example"
    assert repository.name == "project"


def test_parse_github_repository_git_suffix():
    repository = parse_github_repository(
        "https://github.com/example/project.git"
    )

    assert repository.owner == "example"
    assert repository.name == "project"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/example/project",
        "https://gitlab.com/example/project",
        "https://github.com/example",
    ],
)
def test_invalid_github_repository_url(url):
    with pytest.raises(ValueError):
        parse_github_repository(url)
