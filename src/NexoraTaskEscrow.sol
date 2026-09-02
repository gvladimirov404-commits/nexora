// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract NexoraTaskEscrow {
    enum Status {
        Created,
        Funded,
        Submitted,
        Passed,
        Failed,
        Released,
        Refunded
    }

    struct Task {
        address creator;
        address agent;
        address verifier;
        uint256 payment;
        uint256 deadline;
        bytes32 policyHash;
        bytes32 resultHash;
        Status status;
    }

    uint256 public nextTaskId;

    mapping(uint256 => Task) public tasks;
    mapping(uint256 => bytes32) public verificationHashes;

    error InvalidAddress();
    error InvalidPayment();
    error InvalidResultHash();
    error InvalidVerificationHash();
    error InvalidDeadline();
    error TaskNotFound();
    error InvalidStatus();
    error Unauthorized();
    error IncorrectFunding();
    error DeadlineExpired();
    error DeadlineNotReached();
    error TransferFailed();

    event TaskCreated(
        uint256 indexed taskId,
        address indexed creator,
        address indexed agent,
        address verifier,
        uint256 payment,
        uint256 deadline,
        bytes32 policyHash
    );

    event TaskFunded(uint256 indexed taskId, uint256 amount);

    event ResultSubmitted(
        uint256 indexed taskId,
        bytes32 indexed resultHash
    );

    event VerificationDecided(
        uint256 indexed taskId,
        bool passed,
        bytes32 indexed verificationHash
    );

    event PaymentReleased(
        uint256 indexed taskId,
        address indexed agent,
        uint256 amount
    );

    event PaymentRefunded(
        uint256 indexed taskId,
        address indexed creator,
        uint256 amount
    );

    function createTask(
        address agent,
        address verifier,
        uint256 payment,
        uint256 deadline,
        bytes32 policyHash
    ) external returns (uint256 taskId) {
        if (agent == address(0) || verifier == address(0)) {
            revert InvalidAddress();
        }

        if (payment == 0) {
            revert InvalidPayment();
        }

        if (deadline <= block.timestamp) {
            revert InvalidDeadline();
        }

        taskId = nextTaskId++;

        tasks[taskId] = Task({
            creator: msg.sender,
            agent: agent,
            verifier: verifier,
            payment: payment,
            deadline: deadline,
            policyHash: policyHash,
            resultHash: bytes32(0),
            status: Status.Created
        });

        emit TaskCreated(
            taskId,
            msg.sender,
            agent,
            verifier,
            payment,
            deadline,
            policyHash
        );
    }

    function fundTask(uint256 taskId) external payable {
        Task storage task = tasks[taskId];

        if (task.creator == address(0)) {
            revert TaskNotFound();
        }

        if (msg.sender != task.creator) {
            revert Unauthorized();
        }

        if (task.status != Status.Created) {
            revert InvalidStatus();
        }

        if (msg.value != task.payment) {
            revert IncorrectFunding();
        }

        task.status = Status.Funded;

        emit TaskFunded(taskId, msg.value);
    }

    function submitResult(
        uint256 taskId,
        bytes32 resultHash
    ) external {
        Task storage task = tasks[taskId];

        if (task.creator == address(0)) {
            revert TaskNotFound();
        }

        if (msg.sender != task.agent) {
            revert Unauthorized();
        }

        if (task.status != Status.Funded) {
            revert InvalidStatus();
        }

        if (block.timestamp > task.deadline) {
            revert DeadlineExpired();
        }

        if (resultHash == bytes32(0)) {
            revert InvalidResultHash();
        }

        task.resultHash = resultHash;
        task.status = Status.Submitted;

        emit ResultSubmitted(taskId, resultHash);
    }

    function verifyTask(
        uint256 taskId,
        bool passed,
        bytes32 verificationHash
    ) external {
        Task storage task = tasks[taskId];

        if (task.creator == address(0)) {
            revert TaskNotFound();
        }

        if (msg.sender != task.verifier) {
            revert Unauthorized();
        }

        if (task.status != Status.Submitted) {
            revert InvalidStatus();
        }

        if (block.timestamp > task.deadline) {
            revert DeadlineExpired();
        }

        if (verificationHash == bytes32(0)) {
            revert InvalidVerificationHash();
        }

        verificationHashes[taskId] = verificationHash;
        task.status = passed ? Status.Passed : Status.Failed;

        emit VerificationDecided(taskId, passed, verificationHash);
    }

    function releasePayment(uint256 taskId) external {
        Task storage task = tasks[taskId];

        if (task.creator == address(0)) {
            revert TaskNotFound();
        }

        if (task.status != Status.Passed) {
            revert InvalidStatus();
        }

        if (msg.sender != task.creator && msg.sender != task.agent) {
            revert Unauthorized();
        }

        task.status = Status.Released;

        (bool success, ) = payable(task.agent).call{value: task.payment}("");

        if (!success) {
            task.status = Status.Passed;
            revert TransferFailed();
        }

        emit PaymentReleased(taskId, task.agent, task.payment);
    }

    function refundPayment(uint256 taskId) external {
        Task storage task = tasks[taskId];

        if (task.creator == address(0)) {
            revert TaskNotFound();
        }

        if (task.status != Status.Failed) {
            revert InvalidStatus();
        }

        if (msg.sender != task.creator) {
            revert Unauthorized();
        }

        task.status = Status.Refunded;

        (bool success, ) = payable(task.creator).call{value: task.payment}("");

        if (!success) {
            task.status = Status.Failed;
            revert TransferFailed();
        }

        emit PaymentRefunded(taskId, task.creator, task.payment);
    }

    function refundAfterDeadline(uint256 taskId) external {
        Task storage task = tasks[taskId];

        if (task.creator == address(0)) {
            revert TaskNotFound();
        }

        if (msg.sender != task.creator) {
            revert Unauthorized();
        }

        if (task.status != Status.Funded &&
            task.status != Status.Submitted) {
            revert InvalidStatus();
        }

        if (block.timestamp <= task.deadline) {
            revert DeadlineNotReached();
        }

        Status previousStatus = task.status;
        task.status = Status.Refunded;

        (bool success, ) = payable(task.creator).call{value: task.payment}("");

        if (!success) {
            task.status = previousStatus;
            revert TransferFailed();
        }

        emit PaymentRefunded(taskId, task.creator, task.payment);
    }
}
