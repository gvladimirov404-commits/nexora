from types import SimpleNamespace

import pytest

from verifier.registry import (
    UniversalVerificationResult,
    VerifierRegistry,
)


def make_result():
    return UniversalVerificationResult(
        status="PASS",
        policy_hash="policy-123",
        evidence_hash="evidence-456",
        verification_hash="verification-789",
        details={"message": "Generic task verified"},
    )


def test_registry_verifies_task_without_github_fields():
    registry = VerifierRegistry()
    policy = SimpleNamespace(rule="must be valid")
    evidence = SimpleNamespace(proof="proof-data")

    def verifier(received_policy, received_evidence):
        assert received_policy is policy
        assert received_evidence is evidence
        return make_result()

    registry.register("generic_task", verifier)

    result = registry.verify("generic_task", policy, evidence)

    assert result.status == "PASS"
    assert result.policy_hash == "policy-123"
    assert result.evidence_hash == "evidence-456"
    assert result.verification_hash == "verification-789"


def test_registry_rejects_duplicate_task_type():
    registry = VerifierRegistry()
    registry.register("generic_task", lambda policy, evidence: make_result())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            "generic_task",
            lambda policy, evidence: make_result(),
        )


def test_registry_rejects_unknown_task_type():
    registry = VerifierRegistry()

    with pytest.raises(ValueError, match="Unsupported task type"):
        registry.verify("unknown_task", object(), object())


def test_result_rejects_invalid_status():
    with pytest.raises(ValueError, match="status must be PASS or FAIL"):
        UniversalVerificationResult(
            status="UNKNOWN",
            policy_hash="p",
            evidence_hash="e",
            verification_hash="v",
            details={},
        )


def test_registry_rejects_wrong_result_type():
    registry = VerifierRegistry()
    registry.register("generic_task", lambda policy, evidence: {"passed": True})

    with pytest.raises(TypeError, match="must return UniversalVerificationResult"):
        registry.verify("generic_task", object(), object())


def test_engine_universal_entry_accepts_generic_task_without_github_fields():
    from verifier.engine import register_task_verifier, verify_registered_task

    task_type = "registry_smoke_test"

    register_task_verifier(
        task_type,
        lambda policy, evidence: UniversalVerificationResult(
            status="PASS",
            policy_hash="p",
            evidence_hash="e",
            verification_hash="v",
            details={"message": "generic task verified"},
        ),
    )

    result = verify_registered_task(
        SimpleNamespace(task_type=task_type, rule="valid"),
        SimpleNamespace(proof="test-proof"),
    )

    assert result.status == "PASS"
    assert result.details["message"] == "generic task verified"



def _make_external_verifier():
    def verify(policy, evidence):
        passed = evidence.proof == policy.expected_proof
        return UniversalVerificationResult(
            status="PASS" if passed else "FAIL",
            policy_hash="custom-policy-hash",
            evidence_hash="custom-evidence-hash",
            verification_hash="custom-verification-hash",
            details={"checker": "external_module"},
        )

    return verify


def test_external_verifier_accepts_valid_evidence():
    from verifier.engine import (
        register_task_verifier,
        verify_registered_task,
    )

    task_type = "external_valid_evidence_test"
    register_task_verifier(task_type, _make_external_verifier())

    policy = SimpleNamespace(
        task_type=task_type,
        expected_proof="valid-proof",
    )
    evidence = SimpleNamespace(proof="valid-proof")

    result = verify_registered_task(policy, evidence)

    assert result.status == "PASS"
    assert result.details["checker"] == "external_module"


def test_external_verifier_rejects_invalid_evidence():
    from verifier.engine import (
        register_task_verifier,
        verify_registered_task,
    )

    task_type = "external_invalid_evidence_test"
    register_task_verifier(task_type, _make_external_verifier())

    policy = SimpleNamespace(
        task_type=task_type,
        expected_proof="valid-proof",
    )
    evidence = SimpleNamespace(proof="invalid-proof")

    result = verify_registered_task(policy, evidence)

    assert result.status == "FAIL"
    assert result.details["checker"] == "external_module"
