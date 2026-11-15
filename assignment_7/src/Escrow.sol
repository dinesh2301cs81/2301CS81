// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/** @notice Course-only escrow. Buyer deposits once; parties can dispute; arbiter resolves. */
contract Escrow {
    enum State { Created, Funded, Disputed, Released, ResolvedToBuyer, ResolvedToSeller, Cancelled }
    address public immutable buyer;
    address public immutable seller;
    address public immutable arbiter;
    State public state;
    bool public buyerCancelApproved;
    bool public sellerCancelApproved;
    uint256 public deposit;
    mapping(address => uint256) public credit;
    uint256 public liabilities;
    bool private entered;

    error Unauthorized();
    error InvalidAddress();
    error RoleOverlap();
    error WrongState();
    error InvalidAmount();
    error Reentrant();
    error TransferFailed();

    event Funded(address indexed buyer, uint256 amount);
    event CancellationApproved(address indexed who);
    event Cancelled();
    event Released(address indexed seller, uint256 amount);
    event Disputed(address indexed who);
    event Resolved(address indexed payee, uint256 amount);
    event Withdrawal(address indexed payee, uint256 amount);

    constructor(address _buyer, address _seller, address _arbiter) {
        if (_buyer == address(0) || _seller == address(0) || _arbiter == address(0)) revert InvalidAddress();
        if (_buyer == _seller || _buyer == _arbiter || _seller == _arbiter) revert RoleOverlap();
        buyer = _buyer;
        seller = _seller;
        arbiter = _arbiter;
        state = State.Created;
    }
    modifier onlyBuyer() { if (msg.sender != buyer) revert Unauthorized(); _; }
    modifier onlyParty() { if (msg.sender != buyer && msg.sender != seller) revert Unauthorized(); _; }
    modifier onlyArbiter() { if (msg.sender != arbiter) revert Unauthorized(); _; }
    modifier inState(State wanted) { if (state != wanted) revert WrongState(); _; }
    modifier nonReentrant() {
        if (entered) revert Reentrant();
        entered = true;
        _;
        entered = false;
    }
    function fund() external payable onlyBuyer inState(State.Created) {
        if (msg.value == 0) revert InvalidAmount();
        deposit = msg.value;
        liabilities = msg.value;
        state = State.Funded;
        emit Funded(msg.sender, msg.value);
    }
    /// @dev Cancellation is mutual and only permitted from Created; no funds exist then.
    function approveCancellation() external onlyParty inState(State.Created) {
        if (msg.sender == buyer) buyerCancelApproved = true;
        else sellerCancelApproved = true;
        emit CancellationApproved(msg.sender);
        if (buyerCancelApproved && sellerCancelApproved) {
            state = State.Cancelled;
            emit Cancelled();
        }
    }
    function release() external onlyBuyer inState(State.Funded) {
        state = State.Released;
        credit[seller] += deposit;
        emit Released(seller, deposit);
    }
    function dispute() external onlyParty inState(State.Funded) {
        state = State.Disputed;
        emit Disputed(msg.sender);
    }
    function resolve(bool paySeller) external onlyArbiter inState(State.Disputed) {
        address recipient = paySeller ? seller : buyer;
        state = paySeller ? State.ResolvedToSeller : State.ResolvedToBuyer;
        credit[recipient] += deposit;
        emit Resolved(recipient, deposit);
    }
    function withdraw() external nonReentrant {
        uint256 amount = credit[msg.sender];
        if (amount == 0) revert InvalidAmount();
        credit[msg.sender] = 0;
        liabilities -= amount;
        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit Withdrawal(msg.sender, amount);
    }
    // Receive unexpected ETH deliberately disabled; force-sent ETH remains possible via selfdestruct.
    receive() external payable { revert WrongState(); }
    fallback() external payable { revert WrongState(); }
}
