// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import "forge-std/Script.sol";
import "../src/Escrow.sol";
contract Deploy is Script {
    function run() external returns (Escrow escrow) {
        address buyer = vm.envAddress("BUYER");
        address seller = vm.envAddress("SELLER");
        address arbiter = vm.envAddress("ARBITER");
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerKey);
        escrow = new Escrow(buyer, seller, arbiter);
        vm.stopBroadcast();
    }
}
