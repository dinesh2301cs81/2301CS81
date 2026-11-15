# Assignment 1: Hashlab
Python 3.11+; no external runtime dependencies.

Run `python hashlab.py text "Alice pays Bob 10"`, `python hashlab.py hex 616263`, `python hashlab.py file sample.bin`, `python hashlab.py avalanche --text "Alice pays Bob 10" --bit 7`, `python hashlab.py canonical-json sample.json`, or `python hashlab.py demo`.

Canonical JSON policy: UTF-8, lexicographically sorted keys, compact separators, literal Unicode, finite JSON numbers only; no whitespace; Unicode is NOT normalized automatically. A JSON root object is required. Input bit 0 is the least significant bit of the first byte. File hashes use 1 MiB chunks.

Test: `python -m pytest -q`.
Video: demonstrate SHA-256 match against `sha256sum`, LF/CRLF, canonical JSON, avalanche, and a large file.
