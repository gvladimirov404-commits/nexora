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


