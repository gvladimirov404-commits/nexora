// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {NexoraTaskEscrow} from "../src/NexoraTaskEscrow.sol";

contract DeployNexoraTaskEscrow is Script {
    function run() external returns (NexoraTaskEscrow escrow) {
        vm.startBroadcast();
        escrow = new NexoraTaskEscrow();
        vm.stopBroadcast();
    }
}
