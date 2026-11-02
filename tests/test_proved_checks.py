"""Checks the compiler proves are not emitted; unprovable ones still are."""
import re
import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.llvm import LLVMGen


def emit(source):
    program = S.parse(source); hashes = hash_program(program); Checker(program).run()
    return LLVMGen(program.fns, hashes, 'x86_64-unknown-linux-gnu').program()


def body(ir, name):
    """One function's IR with each trap message string inlined."""
    key = next(k for k in ('@ax_' + name + '__seq(', '@ax_' + name + '__par(') if k in ir)
    start = ir.index(key); text = ir[start:ir.index('\n}', start)]
    strings = dict(re.findall(r'^(@[\w.$]+) = private unnamed_addr constant \[\d+ x i8\] c"(.*)\\00"', ir, re.M))
    return re.sub(r'@[\w.$]+', lambda m: '"' + strings[m.group(0)] + '"' if m.group(0) in strings else m.group(0), text)


def loop_body(ir):
    return ir[ir.index('\nloop_cond'):ir.index('\nloop_exit')]


# Interval analysis covers pure functions; effect functions start from unknown inputs.
WORDS = 'fn scan(s:Arr u8 n,start:i64) -> i64 = loop(i=start,done=false) while !done && i>=0 && i<=n-8 next({next}) yield i\n'


class ProvedChecks(unittest.TestCase):
    def test_guarded_word_read_has_no_runtime_bounds(self):
        ir = body(emit(WORDS.replace('{next}', 'i+8,byte_read_le(s,i,8)==0') + 'effect fn main() -> i64 = scan("abcdefghijk",0)'), 'scan')
        self.assertNotIn('byte read', ir)
        ir = body(emit('effect fn scan(s:Arr u8 n,i:i64) -> i64 = byte_read_le(s,i,8)\neffect fn main() -> i64 = scan("abcdefghijk",1)'), 'scan')
        self.assertIn('byte read bounds', ir)

    def test_interval_bounds_discharge_overflow_with_relational_facts(self):
        # i <= n - 8 and count_trailing_zeros(x)/8 <= 8: the step cannot wrap.
        ir = body(emit(WORDS.replace('{next}', 'i+count_trailing_zeros(byte_read_le(s,i,8))/8,true') + 'effect fn main() -> i64 = scan("abcdefghijk",0)'), 'scan')
        self.assertNotIn('integer overflow', ir)
        self.assertIn('add nsw i64', ir)
        # Without the relational guard the same increment keeps its check.
        ir = body(emit('fn step(i:i64,x:i64) -> i64 = i+count_trailing_zeros(x)/8\neffect fn main() -> i64 = step(1,2)'), 'step')
        self.assertIn('integer overflow', ir)

    def test_proven_check_is_dropped_and_unproven_kept(self):
        ir = body(emit('effect fn get(a:Arr i64 n,i:i64) -> i64 = if i>=0 && i<n then check i>=0 && i<n in a[i] else 0\neffect fn main() -> i64 = get(arr(k in 0..3) k,1)'), 'get')
        self.assertNotIn('check failed', ir)
        ir = body(emit('effect fn get(a:Arr i64 n,i:i64) -> i64 = check i>=0 && i<n in a[i]\neffect fn main() -> i64 = get(arr(k in 0..3) k,1)'), 'get')
        self.assertIn('check failed', ir)

    def test_bool_let_keeps_its_condition(self):
        ir = body(emit('effect fn get(s:Arr u8 n,i:i64) -> i64 = let room=i>=0 && i<=n-4 in if room then byte_read_le(s,i,4) else 0\neffect fn main() -> i64 = get("abcdef",1)'), 'get')
        self.assertNotIn('byte read', ir)
        ir = body(emit('effect fn get(s:Arr u8 n,i:i64) -> i64 = let room=i>=0 && i<=n-4 in if !room then byte_read_le(s,i,4) else 0\neffect fn main() -> i64 = get("abcdef",1)'), 'get')
        self.assertIn('byte read bounds', ir)

    def test_cold_functions_stay_out_of_callers(self):
        ir = emit('private cold fn rare(x:i64) -> i64 = x*3\nfn cold_value(cold:i64) -> i64 = cold+1\neffect fn main() -> i64 = rare(2)+cold_value(4)')
        self.assertRegex(ir, r'define internal i64 @ax_rare__\w+\(i64 %p_x\) noinline cold')

    def test_set_only_loop_state_tests_uniqueness_once(self):
        source = ('effect fn fill(a:Arr i64 _) -> Arr i64 _ = loop(i=0,out=a) while i>=0 && i<len(out) next(i+1,set(out,i,7)) yield out\n'
                  'effect fn main() -> i64 = len(fill(arr(k in 0..4) k))')
        ir = body(emit(source), 'fill')
        self.assertIn('unique_copy', ir)
        self.assertNotIn('set_copy', loop_body(ir))
        # A state passed elsewhere inside the loop keeps the per-set test.
        source = 'fn first(a:Arr i64 _) -> i64 = if len(a)>0 then a[0] else 0\n' + source.replace('set(out,i,7)', 'set(out,i,first(out))')
        ir = body(emit(source), 'fill')
        self.assertNotIn('unique_copy', ir)
        self.assertIn('set_copy', loop_body(ir))


if __name__ == '__main__':
    unittest.main()
