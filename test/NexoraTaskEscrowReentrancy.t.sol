// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/NexoraTaskEscrow.sol";

contract ReentrantAgent {
    NexoraTaskEscrow public immutable escrow;
    uint256 public taskId;
    bool public attackEnabled;
    bool public reentered;

    constructor(NexoraTaskEscrow _escrow) {
        escrow = _escrow;
    }

    function configure(uint256 _taskId) external {
        taskId = _taskId;
    }

    function enableAttack() external {
        attackEnabled = true;
    }

    receive() external payable {
        if (attackEnabled && !reentered) {
            reentered = true;

            try escrow.releasePayment(taskId) {
                revert("REENTRANCY_SUCCEEDED");
            } catch {
                // Expected: status was already changed to Released.
            }
        }
    }
}

contract ReentrantCreator {
    NexoraTaskEscrow public immutable escrow;
    uint256 public taskId;
    bool public attackEnabled;
    bool public reentered;

    constructor(NexoraTaskEscrow _escrow) {
        escrow = _escrow;
    }

    function createTaskFor(
        address agent,
        address verifier,
        uint256 payment,
        uint256 deadline,
        bytes32 policyHash
    ) external returns (uint256) {
        taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            policyHash
        );

        return taskId;
    }

    function fundTaskFor(uint256 _taskId) external payable {
        escrow.fundTask{value: msg.value}(_taskId);
    }

    function refundAfterDeadlineFor(uint256 _taskId) external {
        escrow.refundAfterDeadline(_taskId);
    }

    function enableAttack() external {
        attackEnabled = true;
    }

    receive() external payable {
        if (attackEnabled && !reentered) {
            reentered = true;

            try escrow.refundAfterDeadline(taskId) {
                revert("REENTRANCY_SUCCEEDED");
            } catch {
                // Expected: status was already changed to Refunded.
            }
        }
    }
}

contract NexoraTaskEscrowReentrancyTest is Test {
    NexoraTaskEscrow escrow;

    receive() external payable {}

    address verifier = address(0x1001);
    address agent = address(0x1002);

    uint256 payment = 1 ether;
    uint256 deadline;

    function setUp() public {
        escrow = new NexoraTaskEscrow();
        deadline = block.timestamp + 1 days;

        vm.deal(address(this), 10 ether);
        vm.deal(agent, 1 ether);
        vm.deal(verifier, 1 ether);
    }

    function test_ReleasePaymentBlocksReentrancy() public {
        ReentrantAgent maliciousAgent = new ReentrantAgent(escrow);

        uint256 taskId = escrow.createTask(
            address(maliciousAgent),
            verifier,
            payment,
            deadline,
            keccak256("policy-release")
        );

        maliciousAgent.configure(taskId);

        escrow.fundTask{value: payment}(taskId);

        vm.prank(address(maliciousAgent));
        escrow.submitResult(
            taskId,
            keccak256("result-release")
        );

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            true,
            keccak256("verification-release")
        );

        maliciousAgent.enableAttack();

        escrow.releasePayment(taskId);

        assertTrue(maliciousAgent.reentered());
        assertEq(address(escrow).balance, 0);
        assertEq(address(maliciousAgent).balance, payment);
    }

    function test_RefundPaymentCannotBeCalledTwice() public {
        uint256 taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-refund")
        );

        escrow.fundTask{value: payment}(taskId);

        vm.prank(agent);
        escrow.submitResult(
            taskId,
            keccak256("result-failed")
        );

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            false,
            keccak256("verification-failed")
        );

        escrow.refundPayment(taskId);

        vm.expectRevert(NexoraTaskEscrow.InvalidStatus.selector);
        escrow.refundPayment(taskId);

        assertEq(address(escrow).balance, 0);
    }

    function test_RefundAfterDeadlineBlocksReentrancy() public {
        ReentrantCreator maliciousCreator = new ReentrantCreator(escrow);

        uint256 taskId = maliciousCreator.createTaskFor(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-deadline")
        );

        maliciousCreator.fundTaskFor{value: payment}(taskId);

        vm.warp(deadline + 1);

        maliciousCreator.enableAttack();

        maliciousCreator.refundAfterDeadlineFor(taskId);

        assertTrue(maliciousCreator.reentered());
        assertEq(address(escrow).balance, 0);
        assertEq(address(maliciousCreator).balance, payment);
    }
}
