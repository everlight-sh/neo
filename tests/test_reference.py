import unittest
from neoc import syntax as S
from neoc.reference import Reference, Fault
from neoc.fold import Interp, Unfoldable
from neoc.check import Checker
from neoc.graph import hash_program

class ReferenceTests(unittest.TestCase):
    def checked(self,source):
        program=S.parse(source);hash_program(program);Checker(program).run();return program
    def test_reference_and_folder_reject_overflow(self):
        program=self.checked('fn value (x:i64) -> i64 = x + 1 fn main () -> i64 = value(9223372036854775807)')
        with self.assertRaises(Fault):Reference(program).call('main',[])
        with self.assertRaises(Unfoldable):Interp({f.name:f for f in program.fns}).ev(program.fns[-1].body,{})
    def test_array_and_record_value_semantics(self):
        program=self.checked('type Pair = { a:i64,b:i64 } fn main () -> i64 = let a = arr(i in 0..3) i in let b = set(a,0,8) in a[0] + b[0]')
        self.assertEqual(Reference(program).call('main',[]),8)
    def test_explicit_wrapping(self):
        program=self.checked('fn main () -> i64 = wrapping_add(9223372036854775807,1)')
        self.assertEqual(Reference(program).call('main',[]),-(1<<63))
    def test_bit_patterns_match_independent_python_model(self):
        program=self.checked('fn band(a:i64,b:i64)->i64=bit_and(a,b) fn bor(a:i64,b:i64)->i64=bit_or(a,b) fn bxor(a:i64,b:i64)->i64=bit_xor(a,b) fn swap(a:i64,b:i64)->i64=byte_swap64(a) fn high(a:i64,b:i64)->i64=mul_high(a,b) fn main()->i64=0')
        reference=Reference(program);folder=Interp({f.name:f for f in program.fns})
        values=[0,1,-1,-(1<<63),(1<<63)-1,0x0102030405060708]
        signed=lambda n:(n+(1<<63))%(1<<64)-(1<<63)
        for a in values:
            for b in values:
                expected=[signed(a&b),signed(a|b),signed(a^b),signed(int.from_bytes((a%(1<<64)).to_bytes(8,'big'),'little')),signed(((a%(1<<64))*(b%(1<<64)))>>64)]
                for function,want in zip(program.fns,expected):
                    self.assertEqual(reference.call(function.name,[a,b]),want)
                    self.assertEqual(folder.ev(function.body,{'a':a,'b':b}),want)
    def test_overflow_proofs_use_lexical_binding_identity(self):
        program=self.checked('fn main (x:i64{x == 0}) -> i64 = loop (x = 9223372036854775807) while x > 0 next (x + 1) yield x')
        self.assertFalse(program.fns[0].body.nexts[0].arithmetic_proven)
        with self.assertRaises(Fault):Reference(program).call('main',[0])
    def test_only_proven_safe_arithmetic_loses_its_guard(self):
        program=self.checked('fn plain (x:i64) -> i64 = x + 1 fn safe (x:i64{x < 9223372036854775807}) -> i64 = x + 1 fn main () -> i64 = safe(1)')
        self.assertFalse(program.fns[0].body.arithmetic_proven)
        self.assertTrue(program.fns[1].body.arithmetic_proven)
    def test_constant_folder_narrowing_and_reduction(self):
        program=self.checked('fn narrow (x:i64) -> i64 = i64(i32(x)) fn main () -> i64 = narrow(2147483648)')
        self.assertEqual(Interp({f.name:f for f in program.fns}).ev(program.fns[-1].body,{}),-(1<<31))
        program=self.checked('fn total (n:i64{n >= 0}) -> i64 = sum(i in 0..n) 9223372036854775807 fn main () -> i64 = total(2)')
        with self.assertRaises(Unfoldable):Interp({f.name:f for f in program.fns}).ev(program.fns[-1].body,{})

if __name__=='__main__':unittest.main()
