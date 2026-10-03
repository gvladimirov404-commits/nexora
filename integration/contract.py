import json
from pathlib import Path

from web3 import Web3


ABI_PATH = Path(__file__).resolve().parents[1] / "out" / "NexoraTaskEscrow.abi"


def load_contract_abi():
    with ABI_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def create_contract(web3: Web3, address: str):
    return web3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=load_contract_abi(),
    )
