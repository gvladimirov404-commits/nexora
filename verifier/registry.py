from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class UniversalVerificationResult:
    status: str
    policy_hash: str
    evidence_hash: str
    verification_hash: str
    details: dict[str, Any]

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "FAIL"}:
            raise ValueError("status must be PASS or FAIL")


Verifier = Callable[[Any, Any], UniversalVerificationResult]


class VerifierRegistry:
    def __init__(self) -> None:
        self._verifiers: dict[str, Verifier] = {}

    def register(self, task_type: str, verifier: Verifier) -> None:
        if not task_type.strip():
            raise ValueError("task_type must not be empty")

        if task_type in self._verifiers:
            raise ValueError(f"Verifier already registered: {task_type}")
        if not callable(verifier):
            raise TypeError("Verifier must be callable")

        self._verifiers[task_type] = verifier

    def supports(self, task_type: str) -> bool:
        """Return whether a verifier is registered for this task type."""
        return task_type in self._verifiers

    def verify(
        self,
        task_type: str,
        policy: Any,
        evidence: Any,
    ) -> UniversalVerificationResult:
        verifier = self._verifiers.get(task_type)

        if verifier is None:
            raise ValueError(f"Unsupported task type: {task_type}")

        result = verifier(policy, evidence)

        if not isinstance(result, UniversalVerificationResult):
            raise TypeError(
                "Verifier must return UniversalVerificationResult"
            )

        return result
