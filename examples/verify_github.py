import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verifier.github_checker import get_github_default_branch_commit
from verifier.models import Evidence, Policy
from verifier.report import create_verification_report


def main() -> None:
    policy = Policy(
        version="1.0",
        task_type="github_repository",
        repository_visibility="public",
        required_files=[
            "README.md",
            "LICENSE",
        ],
    )

    repository_url = "https://github.com/octocat/Hello-World"
    commit_sha = get_github_default_branch_commit(repository_url)

    evidence = Evidence(
        repository_url=repository_url,
        commit_sha=commit_sha,
    )

    report = create_verification_report(
        policy=policy,
        evidence=evidence,
    )

    print("=== NEXORA VERIFICATION ===")
    print()
    print(f"Repository: {evidence.repository_url}")
    print(f"Commit:     {evidence.commit_sha}")
    print()
    print(f"Repository exists: {report.result.repository_exists}")
    print(f"Repository public: {report.result.repository_public}")

    print("Required files:")
    for filename, exists in report.result.required_files.items():
        print(f"  {filename}: {exists}")

    print()
    print(f"PASSED: {report.result.passed}")
    print()
    print(f"Policy hash:       {report.policy_hash}")
    print(f"Evidence hash:     {report.evidence_hash}")
    print(f"Verification hash: {report.verification_hash}")


if __name__ == "__main__":
    main()
