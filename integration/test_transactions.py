from web3 import Web3

from integration.transactions import (
    encode_create_task,
    encode_submit_result,
    encode_verify_task,
)

w3 = Web3()
contract = "0x0000000000000000000000000000000000000001"
agent = "0x0000000000000000000000000000000000000002"
verifier = "0x0000000000000000000000000000000000000003"
policy_hash = "08954333aa4c963d38b0b733206cc95083710a9aa7931570d3e8c68614e69533"
result_hash = "3ac6269e51a32a61f77fb5ae37446567e18b7b30d9d3b6e193f2c902a929edee"
evidence_hash = "bb011c5f48d67c9e65a3d1a414cb47bd55c6483e1265ddbd2fd7442d198aa11d"

create_data = encode_create_task(
    w3, contract, agent, verifier, 10**18, 9999999999, policy_hash
)

submit_data = encode_submit_result(
    w3, contract, 7, result_hash
)

verify_data = encode_verify_task(
    w3, contract, 7, True, evidence_hash
)

assert create_data.startswith("0x")
assert submit_data.startswith("0x")
assert verify_data.startswith("0x")

print("CREATE TASK: OK")
print("SUBMIT RESULT: OK")
print("VERIFY TASK: OK")
print("INTEGRATION TRANSACTION ENCODING: PASS")


from integration.contract import create_contract
from verifier.arbitrum_erc20 import ERC20TransferCondition
from verifier.arbitrum_policy import ArbitrumERC20Policy
from verifier.canonical import policy_hash as canonical_policy_hash


def test_create_task_uses_canonical_policy_hash():
    policy = ArbitrumERC20Policy(
        version="1",
        chain_id=421614,
        condition=ERC20TransferCondition(
            token="0x9b3541C7ABF9Aa3acD990b3547F64ff476f91DA2",
            sender="0x25011a401e7c67699D098f02bc8A2385fd618232",
            recipient="0x43515aef2d9dd9cadfd3cc4f3282c371ad910684",
            minimum_amount=600,
            deadline=1000,
        ),
    )
    expected_policy_hash = canonical_policy_hash(policy)
    create_data = encode_create_task(w3, contract, agent, verifier, 10**18, 9999999999, expected_policy_hash)
    contract_instance = create_contract(w3, contract)
    _, create_args = contract_instance.decode_function_input(create_data)
    assert create_args["policyHash"].hex() == expected_policy_hash


from integration.transactions import (
    encode_fund_task,
    encode_release_payment,
    encode_refund_payment,
    encode_refund_after_deadline,
)


def test_settlement_encoders_match_contract_abi():
    cases = [
        ("fundTask", encode_fund_task),
        ("releasePayment", encode_release_payment),
        ("refundPayment", encode_refund_payment),
        ("refundAfterDeadline", encode_refund_after_deadline),
    ]

    contract_instance = create_contract(w3, contract)
    for expected_name, encoder in cases:
        data = encoder(w3, contract, 7)
        function, args = contract_instance.decode_function_input(data)
        assert function.fn_name == expected_name
        assert args["taskId"] == 7
