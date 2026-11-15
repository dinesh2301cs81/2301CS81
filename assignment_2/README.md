# Assignment 2: Merkle Trees
Standard SHA-256 with domain separation: leaf SHA256(00 || bytes); parent SHA256(01 || left32 || right32); empty root SHA256(02). Duplicate last child when odd. Proofs require exact tree height and explicit sibling direction; a duplicated sibling must equal the current hash.

Commands: `python merkle.py root transactions.txt`, `python merkle.py prove transactions.txt 2 > proof.json`, `python merkle.py verify 'third transaction' proof.json ROOT_HEX`, `python merkle.py bench`.

For five leaves, level 0 = [L0 L1 L2 L3 L4]; level 1 = [N01 N23 N44]; level 2 = [N0123 N4444]; root = N(N0123,N4444). Proof for L2: sibling L3 RIGHT; sibling N01 LEFT; sibling N4444 RIGHT. Note JSON only contains siblings, not the root.

Tests: `python -m pytest -q`. Bench prints measured construction times for 8, 1024 and 100000 leaves (run on your machine; do not quote unmeasured numbers).
