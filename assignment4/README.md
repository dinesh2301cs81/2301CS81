# Assignment 4: In-memory UTXO ledger
Run `python ledger.py --snapshot ledger.json` to print valid/invalid trace and persist the state. Run `python -m pytest -q` (23 tests).

Format: an outpoint is `<64-hex-txid>:<nonnegative output_index>`. An output is `{value: positive integer <= 2^63-1, address: Base58Check course address}`. Signed transaction is `{version:1, inputs:[{txid,index,public_key,signature}], outputs:[{value,address}]}`; canonical sorted-key compact UTF-8 JSON. Each Ed25519 signature signs canonical JSON of `{version, inputs: inputs without signatures, outputs, signing_input: index}`. TXID = SHA256(canonical signed transaction). Validate every input before atomic copy/swap. Fee = sum(input)-sum(output). No duplicate outpoints. Deterministic coin selection: largest first then sorted outpoint tie break. Change output included when positive. Snapshot JSON keys sorted.

The `mint_for_demo` fixture creates *genesis-only test money*, NOT a production coinbase rule. Signing is for a toy chain. No concurrent writers; persistent crash-safe DB not implemented. Test example: 40 + 70 -> 85 Bob + 23 Alice + 2 fee. Submit twice: second spend rejected and state unchanged.
