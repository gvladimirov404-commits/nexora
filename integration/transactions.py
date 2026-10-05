from __future__ import annotations

from web3 import Web3

from integration.contract import create_contract
from integration.hashes import hex_to_bytes32


def encode_create_task(
    web3: Web3,
    contract_address: str,
    agent: str,
    verifier: str,
    payment: int,
    deadline: int,
    policy_hash: str,
) -> str:
    contract = create_contract(web3, contract_address)

    return contract.functions.createTask(
        Web3.to_checksum_address(agent),
        Web3.to_checksum_address(verifier),
        payment,
        deadline,
        hex_to_bytes32(policy_hash),
    )._encode_transaction_data()


def encode_submit_result(
    web3: Web3,
    contract_address: str,
    task_id: int,
    result_hash: str,
) -> str:
    contract = create_contract(web3, contract_address)

    return contract.functions.submitResult(
        task_id,
        hex_to_bytes32(result_hash),
    )._encode_transaction_data()



def encode_verify_task(
    web3: Web3,
    contract_address: str,
    task_id: int,
    passed: bool,
    evidence_hash: str,
) -> str:
    contract = create_contract(web3, contract_address)

    return contract.functions.verifyTask(
        task_id,
        passed,
        hex_to_bytes32(evidence_hash),
    )._encode_transaction_data()
