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
