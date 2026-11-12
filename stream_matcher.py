"""Starter: repair streaming matching while keeping the public API."""

class StreamMatcher:
    def __init__(self, pattern: bytes):
        if type(pattern) is not bytes:
            raise TypeError("pattern must be exact bytes")
        if not pattern:
            raise ValueError("pattern must not be empty")
        self._pattern = pattern
        self._offset = 0

    def feed(self, chunk: bytes) -> list[int]:
        if type(chunk) is not bytes:
            raise TypeError("chunk must be exact bytes")
        result = []
        start = 0
        while True:
            found = chunk.find(self._pattern, start)
            if found < 0:
                break
            result.append(self._offset + found)
            start = found + len(self._pattern)
        self._offset += len(chunk)
        return result
