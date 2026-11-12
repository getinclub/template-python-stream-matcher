"""Black-box contract checks. No external dependencies."""
import gc
import itertools
import random
import tracemalloc
import unittest
from stream_matcher import StreamMatcher


def oracle(data, pattern):
    return [i for i in range(len(data) - len(pattern) + 1)
            if data[i:i + len(pattern)] == pattern]


class StreamTests(unittest.TestCase):
    def check_stream(self, pattern, chunks):
        matcher = StreamMatcher(pattern)
        data = b''
        for chunk in chunks:
            old_length = len(data)
            data += chunk
            expected = [i for i in oracle(data, pattern)
                        if i + len(pattern) > old_length]
            actual = matcher.feed(chunk)
            self.assertIs(type(actual), list)
            self.assertTrue(all(type(i) is int for i in actual))
            self.assertEqual(actual, expected)

    def test_every_partition(self):
        data = b'abababa'
        for mask in range(1 << (len(data) - 1)):
            cuts = [0] + [i for i in range(1, len(data)) if mask & (1 << (i - 1))] + [len(data)]
            chunks = [data[a:b] for a, b in zip(cuts, cuts[1:])]
            for pattern in [b'a', b'aba', b'ababa', b'bab', b'x']:
                with self.subTest(mask=mask, pattern=pattern):
                    self.check_stream(pattern, [b''] + list(itertools.chain.from_iterable((c, b'') for c in chunks)))

    def test_seeded_oracle(self):
        rng = random.Random(20261111)
        for case in range(250):
            data = bytes(rng.randrange(4) for _ in range(rng.randrange(100)))
            pattern = bytes(rng.randrange(4) for _ in range(rng.randrange(1, 12)))
            chunks, pos = [], 0
            while pos < len(data):
                size = rng.randrange(1, 13)
                chunks.extend([b'', data[pos:pos + size]])
                pos += size
            with self.subTest(case=case):
                self.check_stream(pattern, chunks)

    def test_independent_instances_same_pattern(self):
        a, b = StreamMatcher(b'aba'), StreamMatcher(b'aba')
        self.assertEqual(a.feed(b'ab'), [])
        self.assertEqual(b.feed(b'xaba'), [1])
        self.assertEqual(a.feed(b'a'), [0])
        self.assertEqual(b.feed(b'ba'), [3])

    def test_independent_instances_different_patterns(self):
        a, b = StreamMatcher(b'ab'), StreamMatcher(b'ba')
        self.assertEqual(a.feed(b'a'), [])
        self.assertEqual(b.feed(b'a'), [])
        self.assertEqual(a.feed(b'b'), [0])
        self.assertEqual(b.feed(b'b'), [])
        self.assertEqual(b.feed(b'a'), [1])

    def test_caller_owned_results(self):
        m = StreamMatcher(b'a')
        first = m.feed(b'aa')
        saved = first[:]
        second = m.feed(b'a')
        self.assertEqual(first, saved)
        first.append(-999)
        second.clear()
        self.assertEqual(m.feed(b'a'), [3])

    def test_empty_pattern(self):
        with self.assertRaises(ValueError):
            StreamMatcher(b'')

    def test_large_repeated_prefix(self):
        pattern = b'a' * 4096 + b'b'
        m = StreamMatcher(pattern)
        self.assertEqual(m.feed(b'a' * 100000), [])
        self.assertEqual(m.feed(b'b'), [100000 - 4096])
        self.assertEqual(m.feed(pattern), [100001])

    def test_large_overlap_output(self):
        m = StreamMatcher(b'a' * 1000)
        self.assertEqual(m.feed(b'a' * 20000), list(range(19001)))
        self.assertEqual(m.feed(b'a'), [19001])

    def test_retained_memory_does_not_grow_with_stream(self):
        # Broad allocation-growth check, not a timing test or a mandated layout.
        # Input and output objects are released between feeds. Pattern is fixed.
        tracemalloc.start()
        try:
            m = StreamMatcher(b'needle')
            for i in range(64):
                m.feed(b'x' * 4096 + str(i).encode())
            gc.collect()
            baseline = tracemalloc.get_traced_memory()[0]
            for i in range(1024):
                m.feed(b'x' * 4096 + str(i).encode())
            gc.collect()
            growth = tracemalloc.get_traced_memory()[0] - baseline
            self.assertLess(growth, 256000, 'Retained memory grew with a 4 MiB stream')
            self.assertEqual(m.feed(b'needle'), [
                sum(4096 + len(str(i)) for i in range(64)) +
                sum(4096 + len(str(i)) for i in range(1024))])
        finally:
            tracemalloc.stop()


CASES = [
 ('empty_chunk', b'a', [b'']),
 ('empty_between_prefix', b'abc', [b'a', b'', b'b', b'', b'c']),
 ('one_byte_exact', b'a', [b'a']),
 ('one_byte_many', b'a', [b'aaa', b'a']),
 ('no_match', b'error', [b'good', b'fine']),
 ('equal_whole', b'abc', [b'abc']),
 ('longer_than_stream', b'abcdef', [b'ab', b'c']),
 ('cross_two', b'ERROR', [b'INFO ok\nER', b'ROR disk full\n']),
 ('cross_three', b'abc', [b'a', b'b', b'c']),
 ('one_byte_chunks', b'ababa', list(map(lambda v: bytes([v]), b'xxabababaxx'))),
 ('all_same_overlap', b'aaa', [b'aaaaa']),
 ('split_overlap', b'aaa', [b'aa', b'aaa']),
 ('alternating_overlap', b'abab', [b'abababab']),
 ('split_alternating', b'abab', [b'aba', b'baba', b'b']),
 ('fallback_multiple', b'abababac', [b'abababab', b'abac']),
 ('fallback_prefix', b'aab', [b'aaaa', b'ab']),
 ('embedded_nul', b'\x00a\x00', [b'x\x00', b'a\x00a\x00']),
 ('all_byte_values', bytes(range(256)), [bytes(range(128)), bytes(range(128, 256))]),
 ('high_bytes', b'\xff\xfe', [b'\xff', b'\xfe\xff\xfe']),
 ('utf8_offsets', 'é'.encode(), ['猫'.encode() + b'\xc3', b'\xa9\xc3', b'\xa9']),
 ('utf8_pattern_split', '猫'.encode(), [b'\xe7', b'\x8c', b'\xab']),
 ('case_sensitive', b'ERROR', [b'error Error ERROR']),
 ('regex_literal', b'.*', [b'anything.', b'*.*']),
 ('newline_literal', b'a\nb', [b'xa\n', b'b']),
 ('nonzero_offset', b'abc', [b'x' * 100, b'ab', b'c']),
 ('match_then_partial', b'abc', [b'abcab']),
 ('no_duplicate_empty', b'ab', [b'ab', b'', b'', b'x']),
 ('match_then_mismatch', b'aba', [b'aba', b'x', b'aba']),
 ('prefix_then_unrelated', b'abc', [b'ab', b'xxx', b'abc']),
 ('several_per_call', b'ab', [b'xxabababyyab']),
 ('pattern_longer_chunks', b'abcdefgh', [b'ab', b'cd', b'ef', b'gh']),
]
for name, pattern, chunks in CASES:
    def case(self, p=pattern, cs=chunks):
        self.check_stream(p, cs)
    setattr(StreamTests, 'test_fixture_' + name, case)

class BytesSubclass(bytes):
    pass

INVALID = [('str', 'abc'), ('bytearray', bytearray(b'abc')), ('memoryview', memoryview(b'abc')),
           ('none', None), ('integer', 3), ('list', [97, 98]), ('bool', True),
           ('subclass', BytesSubclass(b'abc'))]
for name, invalid in INVALID:
    def pattern_case(self, value=invalid):
        with self.assertRaises(TypeError):
            StreamMatcher(value)
    def feed_case(self, value=invalid):
        m = StreamMatcher(b'aba')
        self.assertEqual(m.feed(b'xxab'), [])
        with self.assertRaises(TypeError):
            m.feed(value)
        self.assertEqual(m.feed(b'a'), [2])
        self.assertEqual(m.feed(b'ba'), [4])
    setattr(StreamTests, 'test_invalid_pattern_' + name, pattern_case)
    setattr(StreamTests, 'test_invalid_feed_atomic_' + name, feed_case)

if __name__ == '__main__':
    unittest.main()
