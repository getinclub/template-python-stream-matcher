"""Authored smoke fixture, not a live log-service monitor."""
from stream_matcher import StreamMatcher

def main():
    matcher = StreamMatcher(b"ERROR")
    chunks = [b"INFO ok\nER", b"ROR disk full\n"]
    observed = [offset for chunk in chunks for offset in matcher.feed(chunk)]
    expected = [8]
    print("AUTHORED LOG-SEARCH SMOKE CHECK")
    print("bytes received:", sum(map(len, chunks)))
    print("chunks received:", len(chunks))
    print("expected byte offsets:", expected)
    print("observed byte offsets:", observed)
    print("status:", "PASS" if observed == expected else "FAIL")
    return 0 if observed == expected else 1

if __name__ == "__main__":
    raise SystemExit(main())
