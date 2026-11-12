# The Log Search That Missed a Match Between Chunks

An authored log-search smoke check receives 24 bytes in two chunks. It expects a match at byte offset 8, but the starter reports no matches. Repair `StreamMatcher` in `stream_matcher.py`, add regression evidence, and open a PR against `main` in a provisioned learning repository. This package does not provision that repository or contact GetIn.

## Run locally

Python 3.10+; no third-party dependencies.

    python monitor.py
    python -m unittest -v

The monitor exits 1 and the tests intentionally fail on the supplied starter. Keep the monitor and tests intact; repair the implementation. CI runs the same unittest suite on Python 3.10 and 3.12.

## Exact contract

- `StreamMatcher(pattern: bytes)` starts an independent stream. Accept **only exact built-in bytes**, not strings, bytearray, memoryview or bytes subclasses. Invalid type raises `TypeError`; empty bytes raises `ValueError`.
- `feed(chunk: bytes) -> list[int]` accepts only exact built-in bytes. Invalid type raises `TypeError` without consuming bytes or changing any matching state. Empty chunks are valid and return `[]` without advancing the stream.
- The logical stream is the concatenation of every successfully fed chunk. Match the exact byte pattern, case-sensitively. Do not decode, normalize, split lines or interpret regex syntax.
- Return every match whose final byte arrives in this call, in increasing order of its **absolute zero-based byte start offset**. Matches may start in an earlier chunk and may overlap. Report each exactly once. An incomplete prefix is not a match.
- For pattern `b"aaa"`, feeding `b"aa"`, then `b"aaa"`, returns `[]`, then `[0, 1, 2]`. For UTF-8 input offsets count encoded bytes, not Unicode characters.
- Separate instances never share mutable stream state. Returned lists are caller-owned; later calls do not mutate them and caller mutations do not affect matching.
- Pattern length `m >= 1` and chunk sizes are not artificially capped. Preprocessing must be O(m); processing a total of n bytes over c calls must be O(n+c+k), where k is the number of emitted offsets. Retained auxiliary matching state must be O(m), independent of total stream length (apart from the absolute counter's integer representation). Do not retain chunks, accumulated stream history or previous result lists. Per-call returned output may use O(k_call) space.
- No finalization, reset, checkpoint, text or iterator APIs are requested. The next `feed` simply continues the same stream.

The suite includes seeded oracle comparisons, every partition of a small stream, adversarial repeated prefixes, input validation, overlaps, byte semantics and a broad retained-memory regression. Passing finite tests is not proof of asymptotic complexity: reviewers must also inspect the algorithm. Use a prefix automaton or another algorithm meeting the contract, not repeated rescans of a growing history.

## Teaching scope

This is an offline, synthetic incident. It does not read production logs, perform deployment or certify real service reliability. There is no hidden network or database integration. The correct implementation and packaging verification live outside the learner repository under the bundle's `reference/` directory.
