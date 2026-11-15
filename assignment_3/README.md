# Assignment 3: Educational wallet (TEST ONLY)
Install: `python -m pip install -r requirements.txt`.

- `python wallet.py keygen alice.key` creates a development-only Ed25519 private key (mode 0600 on POSIX; Windows ACL protection must be checked separately), displaying PUBLIC key and address, never secret bytes.
- `python wallet.py address alice.key`
- Create `tx.json` using fields from assignment sheet. `sender` must be the keygen address, `recipient` any valid course address, `memo_hash` 64 lowercase hex chars.
- `python wallet.py sign alice.key tx.json signed.json`
- `python wallet.py verify signed.json`

Encoding: JSON object with exactly 7 fields; keys sorted lexicographically, UTF-8 without whitespace, no NaN; signed bytes = canonical JSON bytes. Ed25519 signs those bytes directly, signature is fixed 64 bytes (canonical). Version 1, network `course-testnet`, uint63 amount and nonce, 64 lowercase hex SHA256 memo. Public key is 32 raw Ed25519 bytes. Address = Base58Check(0x6f || RIPEMD160(SHA256(public-key)) || first4(SHA256(SHA256(version || payload)))). Replay protection requires caller-maintained set of (sender,nonce), demonstrated in tests; a CLI verification by itself is stateless.

Threat model: private-key theft and clipboard replacement can redirect funds; rely on OS CSPRNG, verify addresses before signing, avoid phishing URLs, never reuse test keys on mainnet, use persistent nonce tracking in actual chain. SHA/Ed25519 library from `cryptography`; do not write own RNG. Test: `python -m pytest -q`.
