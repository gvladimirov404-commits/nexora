from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from verifier.arbitrum_erc20 import ERC20TransferCondition


@dataclass(frozen=True)
class ArbitrumERC20Policy:
    policy_type: ClassVar[str] = "arbitrum_erc20"
    version: str
    chain_id: int
    condition: ERC20TransferCondition

    def to_condition(self) -> ERC20TransferCondition:
        return self.condition
