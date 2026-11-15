# Assignment 7: Solidity Escrow — Foundry

## Specification / state machine
- Created -> Funded: only buyer calls `fund()` with >0 ETH, exactly once.
- Created -> Cancelled: buyer AND seller separately approve before funding; first approval keeps state Created; second changes to Cancelled.
- Funded -> Released: buyer directs proceeds to seller, credited for withdrawal.
- Funded -> Disputed: buyer OR seller raises a dispute.
- Disputed -> ResolvedToBuyer/ResolvedToSeller: arbiter chooses recipient, credited for withdrawal.
- Released/Resolved*/Cancelled: no further escrow state transitions. `withdraw()` is a distinct post-settlement credit withdrawal, never a repeated escrow payment.

State diagram: `Created -> Funded -> Released`, `Funded -> Disputed -> ResolvedToBuyer | ResolvedToSeller`, `Created -> Cancelled (both approvals)`.

## Install, test and deploy
Requires Foundry `forge`, `cast`, `anvil` and git. Inside assignment_7:

```bash
forge install foundry-rs/forge-std --no-commit
forge test -vv
forge test --gas-report
anvil
```

In another terminal, set `BUYER`, `SELLER`, `ARBITER` to three distinct local Anvil accounts and `PRIVATE_KEY` to the *local test deployer key* (never a funded real key). Run:

```bash
forge script script/Deploy.s.sol:Deploy --rpc-url http://127.0.0.1:8545 --broadcast
# From the deployed address shown in broadcast output:
cast send $ESCROW 'fund()' --value 1ether --private-key $BUYER_PRIVATE_KEY --rpc-url http://127.0.0.1:8545
cast send $ESCROW 'release()' --private-key $BUYER_PRIVATE_KEY --rpc-url http://127.0.0.1:8545
cast send $ESCROW 'withdraw()' --private-key $SELLER_PRIVATE_KEY --rpc-url http://127.0.0.1:8545
cast call $ESCROW 'liabilities()(uint256)' --rpc-url http://127.0.0.1:8545
cast code $ESCROW --rpc-url http://127.0.0.1:8545
```

Review `broadcast/` receipts and record transaction hashes, contract address, emitted events, gas report, ETH balances, and a short demo video. Not run here because Foundry is not installed in this environment.

## Threat model / invariants
- Nonzero unique roles prevent confusion; only designated caller can act.
- Funds are never transferred during release or dispute resolution: `credit` and `liabilities` record obligations, users explicitly withdraw, guarded against reentrancy using checks-effects-interactions.
- `address(this).balance == liabilities` should hold after ordinary actions and withdrawals unless ETH is forcibly transferred; forced ETH could produce excess balance without creating additional liabilities.
- Buyer cannot force cancellation after deposit; disputes must be settled by arbiter (trusted party may refuse to act and lock funds). No time-bounded recovery path.
- Private keys, phishing and compromised arbiter remain risks. Deploy only to a local chain.
