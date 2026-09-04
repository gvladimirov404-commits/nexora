from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(data: Any) -> str:
    canonical = canonical_json(data)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def policy_hash(policy: Any) -> str:
    return sha256_hex(asdict(policy))


def evidence_hash(evidence: Any) -> str:
    return sha256_hex(asdict(evidence))


def verification_hash(result: Any) -> str:
    return sha256_hex(asdict(result))
