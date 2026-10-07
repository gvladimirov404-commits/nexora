from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ERC20TransferObservation:
    token: str
    sender: str
    recipient: str
    amount: int
    timestamp: int | None


@dataclass(frozen=True)
class ERC20TransferCondition:
    token: str
    sender: str
    recipient: str
    minimum_amount: int
    deadline: int


def verify_erc20_transfer(
    condition: ERC20TransferCondition,
    observation: ERC20TransferObservation | None,
) -> VerificationStatus:
    if observation is None:
        return VerificationStatus.UNKNOWN

    if observation.timestamp is None:
        return VerificationStatus.UNKNOWN

    if observation.token.lower() != condition.token.lower():
        return VerificationStatus.FAIL

    if observation.sender.lower() != condition.sender.lower():
        return VerificationStatus.FAIL

    if observation.recipient.lower() != condition.recipient.lower():
        return VerificationStatus.FAIL

    if observation.amount < condition.minimum_amount:
        return VerificationStatus.FAIL

    if observation.timestamp > condition.deadline:
        return VerificationStatus.FAIL

    return VerificationStatus.PASS


def verify_erc20_observations(
    condition: ERC20TransferCondition,
    observations: list[ERC20TransferObservation],
) -> VerificationStatus:
    if not observations:
        return VerificationStatus.UNKNOWN

    for observation in observations:
        if (
            observation.token.lower() == condition.token.lower()
            and observation.sender.lower() == condition.sender.lower()
            and observation.recipient.lower() == condition.recipient.lower()
        ):
            if observation.timestamp is None:
                return VerificationStatus.UNKNOWN

            if (
                observation.amount >= condition.minimum_amount
                and observation.timestamp <= condition.deadline
            ):
                return VerificationStatus.PASS

    return VerificationStatus.FAIL
