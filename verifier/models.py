from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Policy:
    version: str
    task_type: str
    repository_visibility: str
    required_files: List[str]


@dataclass(frozen=True)
class Evidence:
    repository_url: str
    commit_sha: str


@dataclass(frozen=True)
class VerificationResult:
    repository_exists: bool
    repository_public: bool
    required_files: Dict[str, bool]
    passed: bool
