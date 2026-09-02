// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/NexoraTaskEscrow.sol";

contract RejectingReceiver {
    receive() external payable {
        revert("ETH_REJECTED");
    }
}

contract RejectingCreator {
    NexoraTaskEscrow public immutable escrow;

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
        return escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            policyHash
        );
    }

    function fundTaskFor(uint256 taskId) external payable {
        escrow.fundTask{value: msg.value}(taskId);
    }

    function refundAfterDeadlineFor(uint256 taskId) external {
        escrow.refundAfterDeadline(taskId);
    }

    function refundPaymentFor(uint256 taskId) external {
        escrow.refundPayment(taskId);
    }

    receive() external payable {
        revert("ETH_REJECTED");
    }
}

contract NexoraTaskEscrowTransferFailureTest is Test {
    NexoraTaskEscrow escrow;
    RejectingReceiver rejectingAgent;
    RejectingCreator rejectingCreator;

    address creator = address(0x1);
    address agent = address(0x2);
    address verifier = address(0x3);

    uint256 payment = 1 ether;
    uint256 deadline;

    function setUp() public {
        escrow = new NexoraTaskEscrow();
        rejectingAgent = new RejectingReceiver();
        rejectingCreator = new RejectingCreator(escrow);

        deadline = block.timestamp + 1 days;

        vm.deal(address(this), 10 ether);
    }

    function test_ReleasePaymentTransferFailureRestoresPassedState() public {
        uint256 taskId = escrow.createTask(
            address(rejectingAgent),
            verifier,
            payment,
            deadline,
            keccak256("policy-release-failure")
        );

        escrow.fundTask{value: payment}(taskId);

        vm.prank(address(rejectingAgent));
        escrow.submitResult(
            taskId,
            keccak256("result-release-failure")
        );

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            true,
            keccak256("verification-release-failure")
        );

        vm.expectRevert(NexoraTaskEscrow.TransferFailed.selector);
        escrow.releasePayment(taskId);

        (
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            NexoraTaskEscrow.Status status
        ) = escrow.tasks(taskId);

        assertEq(
            uint256(status),
            uint256(NexoraTaskEscrow.Status.Passed)
        );

        assertEq(address(escrow).balance, payment);
    }

    function test_RefundPaymentTransferFailureRestoresFailedState() public {
        uint256 taskId = rejectingCreator.createTaskFor(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-refund-failure")
        );

        rejectingCreator.fundTaskFor{value: payment}(taskId);

        vm.prank(agent);
        escrow.submitResult(
            taskId,
            keccak256("result-refund-failure")
        );

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            false,
            keccak256("verification-refund-failure")
        );

        vm.expectRevert(NexoraTaskEscrow.TransferFailed.selector);
        rejectingCreator.refundPaymentFor(taskId);

        (
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            NexoraTaskEscrow.Status status
        ) = escrow.tasks(taskId);

        assertEq(
            uint256(status),
            uint256(NexoraTaskEscrow.Status.Failed)
        );

        assertEq(address(escrow).balance, payment);
    }

    function test_RefundAfterDeadlineTransferFailureRestoresFundedState() public {
        uint256 taskId = rejectingCreator.createTaskFor(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-deadline-failure")
        );

        rejectingCreator.fundTaskFor{value: payment}(taskId);

        vm.warp(deadline + 1);

        vm.expectRevert(NexoraTaskEscrow.TransferFailed.selector);
        rejectingCreator.refundAfterDeadlineFor(taskId);

        (
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            NexoraTaskEscrow.Status status
        ) = escrow.tasks(taskId);

        assertEq(
            uint256(status),
            uint256(NexoraTaskEscrow.Status.Funded)
        );

        assertEq(address(escrow).balance, payment);
    }

    function test_RefundAfterDeadlineTransferFailureRestoresSubmittedState() public {
        uint256 taskId = rejectingCreator.createTaskFor(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-submitted-deadline-failure")
        );

        rejectingCreator.fundTaskFor{value: payment}(taskId);

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result"));

        vm.warp(deadline + 1);

        vm.expectRevert(NexoraTaskEscrow.TransferFailed.selector);
        rejectingCreator.refundAfterDeadlineFor(taskId);

        (
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            NexoraTaskEscrow.Status status
        ) = escrow.tasks(taskId);

        assertEq(
            uint256(status),
            uint256(NexoraTaskEscrow.Status.Submitted)
        );

        assertEq(address(escrow).balance, payment);
    }

}
