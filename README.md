# NEXORA

## Policy-Verified Task Escrow for AI Agents

NEXORA is a smart-contract MVP for controlled settlement of tasks performed by AI agents.

The core principle is:

**Agent → Task → Policy → Verification → Decision → Settlement**

An agent claiming that a task is complete is not, by itself, sufficient to release payment.

The escrow records the task, the agreed policy identifier, the submitted result, the verification decision, and the settlement state.

---

## Current MVP

The current implementation is a Solidity escrow contract:

`src/NexoraTaskEscrow.sol`

It supports the following lifecycle:

```text
Created
   ↓
Funded
   ↓
Submitted
   ↓
Passed ─────→ Released
   │
   └────────→ Failed ─────→ Refunded


## Architecture

Agent → Task → Policy → Evidence → Verification → Decision → Settlement

The policy defines what must be achieved. Evidence describes what was produced. The verification layer evaluates the evidence before settlement.

## MVP

The MVP verifies GitHub repository delivery tasks.

A policy defines the required conditions. Evidence identifies the repository and commit. An off-chain verifier checks the evidence and produces a PASS or FAIL result.

The smart contract stores hashes of the policy, result, and verification evidence and controls payment settlement.

## Smart Contract

`src/NexoraTaskEscrow.sol` implements the on-chain escrow lifecycle.

It records the task creator, agent, verifier, payment, deadline, policy hash, result hash, verification hash, and settlement status.

Only the authorized verifier can submit the verification decision. Payment is released only after a successful verification decision.

## Verification Layer

NEXORA separates task execution from task verification.

The agent submits a result, but the result alone does not authorize payment. The verifier checks the submitted evidence against the task policy and records a cryptographic verification commitment.

This creates a clear separation between execution, verification, and settlement.

## Testing

Solidity tests:

```bash
forge test --use /data/data/com.termux/files/usr/bin/solc
```

Python verifier tests:

```bash
python -m pytest -q verifier_tests
```
