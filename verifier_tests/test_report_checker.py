from dataclasses import dataclass

from verifier.report_checker import verify_report


@dataclass(frozen=True)
class ReportPolicy:
    version: str
    task_type: str
    required_sections: list[str]


@dataclass(frozen=True)
class ReportEvidence:
    content: str | None


def test_report_passes_when_all_sections_exist():
    policy = ReportPolicy(
        version="1",
        task_type="report",
        required_sections=["Summary", "Findings", "Conclusion"],
    )
    evidence = ReportEvidence(
        content="# Summary\nKey points.\n# Findings\nThree findings.\n# Conclusion\nDone."
    )

    result = verify_report(policy, evidence)

    assert result.status == "PASS"
    assert result.details["passed"] is True
    assert all(result.details["required_sections"].values())
    assert len(result.policy_hash) == 64
    assert len(result.evidence_hash) == 64
    assert len(result.verification_hash) == 64


def test_report_fails_when_a_section_is_missing():
    policy = ReportPolicy(
        version="1",
        task_type="report",
        required_sections=["Summary", "Findings", "Conclusion"],
    )
    evidence = ReportEvidence(
        content="# Summary\nKey points.\n# Findings\nThree findings."
    )

    result = verify_report(policy, evidence)

    assert result.status == "FAIL"
    assert result.details["passed"] is False
    assert result.details["required_sections"]["Conclusion"] is False


def test_report_fails_when_content_is_not_text():
    policy = ReportPolicy(
        version="1",
        task_type="report",
        required_sections=["Summary"],
    )
    evidence = ReportEvidence(content=None)

    result = verify_report(policy, evidence)

    assert result.status == "FAIL"



def test_report_is_available_through_public_registry_interface():
    from verifier.engine import verify_registered_task

    policy = ReportPolicy(
        version="1",
        task_type="report",
        required_sections=["Summary", "Conclusion"],
    )
    evidence = ReportEvidence(
        content="# Summary\nOverview\n# Conclusion\nComplete."
    )

    result = verify_registered_task(policy, evidence)

    assert result.status == "PASS"
    assert result.details["task_type"] == "report"


def test_report_does_not_accept_section_name_in_ordinary_sentence():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["Summary"])
    evidence = ReportEvidence(content="The Summary section was not written.")
    result = verify_report(policy, evidence)
    assert result.status == "FAIL"
    assert result.details["required_sections"]["Summary"] is False



def test_report_accepts_case_insensitive_heading_with_closing_hashes():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["Summary"])
    evidence = ReportEvidence(content="### sUmMaRy ###\nBody.")
    result = verify_report(policy, evidence)
    assert result.status == "PASS"


def test_report_does_not_accept_empty_heading_as_required_section():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["Summary"])
    evidence = ReportEvidence(content="#\n## \nThe Summary is missing.")
    result = verify_report(policy, evidence)
    assert result.status == "FAIL"
    assert result.details["required_sections"]["Summary"] is False


def test_report_rejects_blank_required_section_name():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["   "])
    evidence = ReportEvidence(content="# Summary\nBody.")
    result = verify_report(policy, evidence)
    assert result.status == "FAIL"


def test_report_does_not_accept_heading_inside_fenced_code_block():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["Summary"])
    evidence = ReportEvidence(content="Example:\n```markdown\n# Summary\n```\n")
    result = verify_report(policy, evidence)
    assert result.status == "FAIL"
    assert result.details["required_sections"]["Summary"] is False


def test_report_does_not_accept_heading_inside_tilde_fenced_code_block():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["Summary"])
    evidence = ReportEvidence(content="~~~markdown\n# Summary\n~~~\n")
    result = verify_report(policy, evidence)
    assert result.status == "FAIL"
    assert result.details["required_sections"]["Summary"] is False


def test_report_accepts_real_heading_after_fenced_code_block():
    policy = ReportPolicy(version="1", task_type="report", required_sections=["Summary"])
    evidence = ReportEvidence(content="~~~markdown\n# Example\n~~~\n# Summary\nBody.")
    result = verify_report(policy, evidence)
    assert result.status == "PASS"
    assert result.details["required_sections"]["Summary"] is True
