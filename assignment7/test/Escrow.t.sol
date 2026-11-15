// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import "forge-std/Test.sol";
import "../src/Escrow.sol";

contract EscrowTest is Test {
    address buyer = makeAddr("buyer");
    address seller = makeAddr("seller");
    address arbiter = makeAddr("arbiter");
    address stranger = makeAddr("stranger");
    Escrow e;
    function setUp() public { e = new Escrow(buyer, seller, arbiter); vm.deal(buyer, 100 ether); }
    function fund(uint256 amount) internal {
        vm.prank(buyer); e.fund{value: amount}();
    }
    function testFundReleaseWithdraw() public {
        fund(2 ether);
        assertEq(uint256(e.state()), uint256(Escrow.State.Funded));
        assertEq(address(e).balance, e.liabilities());
        vm.prank(buyer); e.release();
        assertEq(e.credit(seller), 2 ether);
        uint256 beforeBalance = seller.balance;
        vm.prank(seller); e.withdraw();
        assertEq(seller.balance - beforeBalance, 2 ether);
        assertEq(address(e).balance, e.liabilities());
        assertEq(e.liabilities(), 0);
    }
    function testDisputeBuyerRefund() public {
        fund(3 ether);
        vm.prank(seller); e.dispute();
        vm.prank(arbiter); e.resolve(false);
        assertEq(e.credit(buyer), 3 ether);
        vm.prank(buyer); e.withdraw();
        assertEq(e.liabilities(), 0);
    }
    function testDisputeSellerWins() public {
        fund(1 ether);
        vm.prank(buyer); e.dispute();
        vm.prank(arbiter); e.resolve(true);
        assertEq(e.credit(seller), 1 ether);
    }
    function testMutualCancellation() public {
        vm.prank(buyer); e.approveCancellation();
        assertEq(uint256(e.state()), uint256(Escrow.State.Created));
        vm.prank(seller); e.approveCancellation();
        assertEq(uint256(e.state()), uint256(Escrow.State.Cancelled));
        vm.prank(buyer); vm.expectRevert(Escrow.WrongState.selector); e.fund{value: 1 ether}();
    }
    function testUnauthorizedActions() public {
        vm.prank(stranger); vm.expectRevert(Escrow.Unauthorized.selector); e.fund{value: 1 ether}();
        fund(1 ether);
        vm.prank(stranger); vm.expectRevert(Escrow.Unauthorized.selector); e.dispute();
        vm.prank(seller); vm.expectRevert(Escrow.Unauthorized.selector); e.release();
        vm.prank(buyer); e.dispute();
        vm.prank(buyer); vm.expectRevert(Escrow.Unauthorized.selector); e.resolve(true);
    }
    function testRepeatedAndForbiddenTransitions() public {
        fund(1 ether);
        vm.prank(buyer); vm.expectRevert(Escrow.WrongState.selector); e.fund{value: 1 ether}();
        vm.prank(buyer); e.release();
        vm.prank(buyer); vm.expectRevert(Escrow.WrongState.selector); e.release();
        vm.prank(seller); vm.expectRevert(Escrow.WrongState.selector); e.dispute();
        vm.prank(seller); e.withdraw();
        vm.prank(seller); vm.expectRevert(Escrow.InvalidAmount.selector); e.withdraw();
    }
    function testInvalidConstructor() public {
        vm.expectRevert(Escrow.InvalidAddress.selector); new Escrow(address(0), seller, arbiter);
        vm.expectRevert(Escrow.RoleOverlap.selector); new Escrow(buyer, buyer, arbiter);
    }
    function testFuzzAmountAndRoles(uint96 raw, bool sellerWins) public {
        uint256 amount = bound(uint256(raw), 1, 90 ether);
        fund(amount);
        vm.prank(seller); e.dispute();
        vm.prank(arbiter); e.resolve(sellerWins);
        address winner = sellerWins ? seller : buyer;
        assertEq(e.credit(winner), amount);
        assertEq(address(e).balance, e.liabilities());
        vm.prank(winner); e.withdraw();
        assertEq(address(e).balance, e.liabilities());
    }
}
