"""Loop states written only in place need no per-iteration uniqueness test.

`set` states already had this; byte_write_le/byte_copy writers, conditional
writes and read-then-write successors now share it. Aliasing uses keep it.
"""
import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.llvm import LLVMGen


def loop_ir(source, name='f'):
    program = S.parse(source + '\neffect fn main() -> i64 = len(f(arr(i in 0..32) u8(i)))')
    hashes = hash_program(program); Checker(program).run()
    ir = LLVMGen(program.fns, hashes, 'x86_64-unknown-linux-gnu').program()
    start = ir.index('@ax_' + name + '__seq('); text = ir[start:ir.index('\n}', start)]
    return text[text.index('\nloop_cond'):text.index('\nloop_exit')]


def checks_uniqueness(source): return 'unique_' in loop_ir(source)


HEAD = 'fn f(a:Arr u8 _) -> Arr u8 _ = loop(i = 0, out = a) while i >= 0 && i + 8 <= len(out) '


class WriteOnlyLoops(unittest.TestCase):
    def test_in_place_writers_skip_the_test(self):
        for nxt in ['next(i + 1, byte_write_le(out, i, i, 1)) yield out',
                    'next(i + 1, set(out, i, u8(i))) yield out',
                    'next(i + 1, byte_copy(out, i, "abcd")) yield out',
                    # dfl_copy's shape: read a word of the state, then write it back further on
                    'next(i + 1, let w = byte_read_le(out, i, 8) in byte_write_le(out, i, w, 8)) yield out',
                    # dispatch-selected writes; the other arm passes the state through
                    'next(i + 1, if i % 3 == 0 then byte_write_le(out, i, 1, 2) else if i % 3 == 1 then set(out, i, u8(2)) else out) yield out',
                    'next(i + 2, byte_write_le(set(out, i, u8(60)), i + 1, 62, 1)) yield out',
                    'next(i + 1, check len(out) > 0 in byte_write_le(out, i, 7, 1)) yield out']:
            with self.subTest(nxt=nxt):
                self.assertFalse(checks_uniqueness(HEAD + nxt))

    def test_sharing_uses_keep_the_test_or_copy(self):
        for nxt in [# the state is aliased by a slice that outlives the write
                    'next(i + 1, let s = byte_slice(out, 0, 1) in byte_write_le(out, i, i64(s[0]), 1)) yield out',
                    # copying the state into itself
                    'next(i + 1, byte_copy(out, i, out)) yield out',
                    # a let rebinding the state's name to another buffer
                    'next(i + 1, let out = a in byte_write_le(out, i, i, 1)) yield out']:
            with self.subTest(nxt=nxt):
                source = HEAD + nxt
                self.assertTrue(checks_uniqueness(source) or 'bytes_copy' in loop_ir(source) or 'set_copy' in loop_ir(source))
        # A second state holding the first one's previous value.
        # The write cannot take the buffer, so it copies.
        source = 'fn f(a:Arr u8 _) -> Arr u8 _ = loop(i = 0, out = a, old = a) while i >= 0 && i + 8 <= len(out) next(i + 1, byte_write_le(out, i, i, 1), out) yield old'
        self.assertIn('bytes_copy', loop_ir(source))

    def test_yield_does_not_inherit_the_exemption(self):
        source = HEAD + 'next(i + 1, set(out, i, u8(1))) yield let s = byte_slice(out, 0, 1) in concat(s, set(out, 0, u8(2)))'
        program = S.parse(source + '\neffect fn main() -> i64 = len(f(arr(i in 0..32) u8(i)))')
        hashes = hash_program(program); Checker(program).run()
        ir = LLVMGen(program.fns, hashes, 'x86_64-unknown-linux-gnu').program()
        start = ir.index('@ax_f__seq('); text = ir[start:ir.index('\n}', start)]
        self.assertIn('unique_', text[text.index('\nloop_exit'):])



RUN = 'type Run = { out : Arr u8 _, n : i64 }\n'
STEP = 'fn step(move r : Run) -> Run = let n = r.n in let out = r.out in if n >= 0 && n < len(out) then Run { out = byte_write_le(out, n, 7, 1), n = n + 1 } else Run { out = out, n = n }\n'


def function_ir(source, name, unique_flags=True):
    program = S.parse(source); hashes = hash_program(program); Checker(program).run()
    ir = LLVMGen(program.fns, hashes, 'x86_64-unknown-linux-gnu', unique_flags=unique_flags).program()
    key = next(k for k in ('@ax_' + name + '__seq(', '@ax_' + name + '__par(') if k in ir)
    start = ir.index(key); return ir[start:ir.index('\n}', start)]


class UniqueFlags(unittest.TestCase):
    MAIN = 'fn main() -> i64 = let r = loop(s = Run { out = arr(i in 0..8) u8(0), n = 0 }) while s.n < 8 next(step(s)) yield s in len(r.out)'

    def test_moved_record_buffer_trusts_the_flag(self):
        ir = function_ir(RUN + STEP + self.MAIN, 'step')
        trust = ir.index('icmp eq i64'); test = ir.index('unique_raw')
        self.assertRegex(ir, r'icmp eq i64 %t\d+, 3')
        self.assertLess(trust, test)                       # the flag is read before the count
        self.assertIn('i64 3, 2', ir)                      # the result carries UNIQUE
        self.assertNotRegex(function_ir(RUN + STEP + self.MAIN, 'step', unique_flags=False), r'icmp eq i64 %t\d+, 3')

    def test_sharing_slots_clear_the_flag_on_moves(self):
        shared = STEP.replace('let out = r.out in', 'let s = byte_slice(r.out, 0, 1) in let out = r.out in').replace('byte_write_le(out, n, 7, 1)', 'byte_write_le(out, n, len(s), 1)')
        ir = function_ir(RUN + shared + self.MAIN, 'step')
        self.assertRegex(ir, r'select i1 %t\d+, i64 1, i64 %t\d+')
        # A slot used only by moves and observers keeps the flag: no clearing select.
        self.assertNotRegex(function_ir(RUN + STEP + self.MAIN, 'step'), r'select i1 %t\d+, i64 1, i64 %t\d+')


if __name__ == '__main__':
    unittest.main()
