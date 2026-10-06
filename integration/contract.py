import json
from pathlib import Path

from web3 import Web3


ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "out" / "NexoraTaskEscrow.sol" / "NexoraTaskEscrow.json"


def load_contract_abi():
    with ARTIFACT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)["abi"]


def create_contract(web3: Web3, address: str):
    return web3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=load_contract_abi(),
    )
