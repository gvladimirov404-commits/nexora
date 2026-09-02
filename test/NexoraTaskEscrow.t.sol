pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {NexoraTaskEscrow} from "../src/NexoraTaskEscrow.sol";

contract NexoraTaskEscrowTest is Test {
    NexoraTaskEscrow escrow;

    address creator = address(0x1);
    address agent = address(0x2);
    address verifier = address(0x3);
    address attacker = address(0x4);

    uint256 payment = 1 ether;
    uint256 deadline;

    function setUp() public {
        escrow = new NexoraTaskEscrow();
        deadline = block.timestamp + 1 days;

        vm.deal(creator, 10 ether);
        vm.deal(agent, 1 ether);
        vm.deal(verifier, 1 ether);
        vm.deal(attacker, 1 ether);
    }

    function createAndFundTask() internal returns (uint256 taskId) {
        vm.prank(creator);

        taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-v1")
        );

        vm.prank(creator);
        escrow.fundTask{value: payment}(taskId);
    }

    function test_CreateTask() public {
        vm.prank(creator);

        uint256 taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-v1")
        );

        (
            address taskCreator,
            address taskAgent,
            address taskVerifier,
            uint256 taskPayment,
            uint256 taskDeadline,
            bytes32 policyHash,
            bytes32 resultHash,
            NexoraTaskEscrow.Status status
        ) = escrow.tasks(taskId);

        assertEq(taskCreator, creator);
        assertEq(taskAgent, agent);
        assertEq(taskVerifier, verifier);
        assertEq(taskPayment, payment);
        assertEq(taskDeadline, deadline);
        assertEq(policyHash, keccak256("policy-v1"));
        assertEq(resultHash, bytes32(0));
        assertEq(uint256(status), uint256(NexoraTaskEscrow.Status.Created));
    }

    function test_CreateTaskRejectsExpiredDeadline() public {
        vm.prank(creator);
        vm.expectRevert(NexoraTaskEscrow.InvalidDeadline.selector);
        escrow.createTask(
            agent,
            verifier,
            payment,
            block.timestamp,
            keccak256("policy-expired")
        );
    }

    function test_SubmitResultAllowedAtExactDeadline() public {
        uint256 taskId = createAndFundTask();

        vm.warp(deadline);

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-at-deadline"));

        (, , , , , , bytes32 storedResultHash, NexoraTaskEscrow.Status status) =
            escrow.tasks(taskId);

        assertEq(storedResultHash, keccak256("result-at-deadline"));
        assertEq(uint256(status), uint256(NexoraTaskEscrow.Status.Submitted));
    }

    function test_SubmitResultRejectsAfterDeadline() public {
        uint256 taskId = createAndFundTask();

        vm.warp(deadline + 1);

        vm.prank(agent);
        vm.expectRevert(NexoraTaskEscrow.DeadlineExpired.selector);
        escrow.submitResult(taskId, keccak256("late-result"));
    }

    function test_VerifyTaskRejectsAfterDeadline() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.warp(deadline + 1);

        vm.prank(verifier);
        vm.expectRevert(NexoraTaskEscrow.DeadlineExpired.selector);
        escrow.verifyTask(
            taskId,
            true,
            keccak256("verification-late")
        );
    }

    function test_FundTask() public {
        uint256 taskId = createAndFundTask();

        assertEq(address(escrow).balance, payment);

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

        assertEq(uint256(status), uint256(NexoraTaskEscrow.Status.Funded));
    }

    function test_FundTaskRejectsIncorrectAmount() public {
        vm.prank(creator);
        uint256 taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-v1")
        );

        vm.prank(creator);
        vm.expectRevert(NexoraTaskEscrow.IncorrectFunding.selector);
        escrow.fundTask{value: payment - 1}(taskId);
    }

    function test_FundTaskRejectsOverpayment() public {
        vm.prank(creator);
        uint256 taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-v1")
        );

        vm.prank(creator);
        vm.expectRevert(NexoraTaskEscrow.IncorrectFunding.selector);
        escrow.fundTask{value: payment + 1}(taskId);
    }

    function test_FundTaskCannotBeCalledTwice() public {
        uint256 taskId = createAndFundTask();

        vm.prank(creator);
        vm.expectRevert(NexoraTaskEscrow.InvalidStatus.selector);
        escrow.fundTask{value: payment}(taskId);
    }

    function test_SubmitResultRejectsEmptyResultHash() public {
        vm.prank(creator);
        uint256 taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            bytes32(uint256(1))
        );

        vm.prank(creator);
        escrow.fundTask{value: payment}(taskId);

        vm.prank(agent);
        vm.expectRevert(NexoraTaskEscrow.InvalidResultHash.selector);
        escrow.submitResult(taskId, bytes32(0));
    }

    function test_SubmitResult() public {
        uint256 taskId = createAndFundTask();
        bytes32 resultHash = keccak256("result-v1");

        vm.prank(agent);
        escrow.submitResult(taskId, resultHash);

        (
            ,
            ,
            ,
            ,
            ,
            ,
            bytes32 storedResultHash,
            NexoraTaskEscrow.Status status
        ) = escrow.tasks(taskId);

        assertEq(storedResultHash, resultHash);
        assertEq(uint256(status), uint256(NexoraTaskEscrow.Status.Submitted));
    }

    function test_VerifyPassedAndReleasePayment() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.prank(verifier);
        escrow.verifyTask(taskId, true, keccak256("verification-v1"));

        uint256 beforeBalance = agent.balance;

        vm.prank(agent);
        escrow.releasePayment(taskId);

        assertEq(agent.balance, beforeBalance + payment);
        assertEq(address(escrow).balance, 0);

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

        assertEq(uint256(status), uint256(NexoraTaskEscrow.Status.Released));
    }

    function test_VerifyFailedAndRefund() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("bad-result"));

        vm.prank(verifier);
        escrow.verifyTask(taskId, false, keccak256("verification-failed-v1"));

        uint256 beforeBalance = creator.balance;

        vm.prank(creator);
        escrow.refundPayment(taskId);

        assertEq(creator.balance, beforeBalance + payment);
        assertEq(address(escrow).balance, 0);

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

        assertEq(uint256(status), uint256(NexoraTaskEscrow.Status.Refunded));
    }

    function test_AttackerCannotRefundFailedTask() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("bad-result"));

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            false,
            keccak256("verification-failed-v2")
        );

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.refundPayment(taskId);
    }

    function test_AttackerCannotRefundAfterDeadline() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("late-result"));

        vm.warp(deadline + 1);

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.refundAfterDeadline(taskId);
    }

    function test_RefundAfterDeadline() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("late-result"));

        vm.warp(deadline + 1);

        uint256 beforeBalance = creator.balance;

        vm.prank(creator);
        escrow.refundAfterDeadline(taskId);

        assertEq(creator.balance, beforeBalance + payment);
        assertEq(address(escrow).balance, 0);
    }

    function test_RevertUnauthorizedFunding() public {
        vm.prank(creator);

        uint256 taskId = escrow.createTask(
            agent,
            verifier,
            payment,
            deadline,
            keccak256("policy-v1")
        );

        vm.deal(attacker, payment);

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.fundTask{value: payment}(taskId);
    }

    function test_RevertUnauthorizedSubmission() public {
        uint256 taskId = createAndFundTask();

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.submitResult(taskId, keccak256("fake-result"));
    }

    function test_RevertUnauthorizedVerification() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.verifyTask(taskId, true, keccak256("verification-v2"));
    }
    
    function test_CannotReleasePaymentTwice() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.prank(verifier);
        escrow.verifyTask(taskId, true, keccak256("verification-v3"));

        vm.prank(agent);
        escrow.releasePayment(taskId);

        vm.expectRevert(NexoraTaskEscrow.InvalidStatus.selector);
        vm.prank(agent);
        escrow.releasePayment(taskId);
    }

    
    function test_VerificationRequiresEvidence() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.prank(verifier);
        vm.expectRevert(NexoraTaskEscrow.InvalidVerificationHash.selector);
        escrow.verifyTask(taskId, true, bytes32(0));
    }


    function test_UnauthorizedCannotReleaseAfterVerification() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            true,
            keccak256("verification-v1")
        );

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.releasePayment(taskId);
    }


    function test_AttackerCannotReleasePayment() public {
        uint256 taskId = createAndFundTask();

        vm.prank(agent);
        escrow.submitResult(taskId, keccak256("result-v1"));

        vm.prank(verifier);
        escrow.verifyTask(
            taskId,
            true,
            keccak256("verification-v1")
        );

        vm.prank(attacker);
        vm.expectRevert(NexoraTaskEscrow.Unauthorized.selector);
        escrow.releasePayment(taskId);
    }


    function test_FundTaskRejectsUnknownTask() public {
        vm.prank(creator);
        vm.expectRevert(NexoraTaskEscrow.TaskNotFound.selector);
        escrow.fundTask(999);
    }

}
