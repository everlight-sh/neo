import unittest
from neoc.syntax import parse
from neoc.graph import hash_program
from neoc.check import Checker, CheckError
from neoc.reference import Reference

class Callbacks(unittest.TestCase):
    def program(self, source):
        p = parse(source); hash_program(p); Checker(p).run(); return p

    def test_pure_values_capture_and_indirect_reference_evaluator(self):
        p = self.program('''type Closure={callback:Fn(i64,i64)->i64,capture:i64}
fn add(a:i64,b:i64)->i64=a+b
fn apply(c:Closure,x:i64)->i64=let invoke=c.callback in invoke(c.capture,x)
fn main()->i64=apply(Closure { callback=function(add),capture=35 },7)''')
        self.assertEqual(Reference(p).call('main', []),42)

    def test_effects_cannot_be_hidden_behind_callbacks(self):
        for source in [
            'effect(fs) fn emit(x:i64)->unit=noop() fn main()->unit=let call=function(emit) in call(1)',
            'effect(fs) fn emit(x:i64)->unit=noop() effect(net) fn main()->unit=let call=function(emit) in call(1)',
            'fn helper(call:Effect<fs>(i64)->unit)->unit=call(1) fn main()->i64=0',
            'type Box={call:Effect<bogus>(i64)->unit} fn main()->i64=0',
        ]:
            with self.subTest(source=source), self.assertRaises(CheckError):self.program(source)

    def test_unsafe_signatures_cannot_erase_obligations(self):
        cases=[
            'fn f(a:Arr u8 n,b:Arr u8 n)->i64=len(a) fn main()->i64=let g=function(f) in g("a","bb")',
            'fn f(n:i64,a:Arr u8 n)->i64=len(a) fn main()->i64=let g=function(f) in g(3,"a")',
            'fn f(a:Arr u8 (4))->i64=a[3] fn main()->i64=let g=function(f) in g("a")',
            'fn f(x:i64{x>0})->i64=x fn main()->i64=let g=function(f) in g(-1)',
            'effect fn f(x:i64)->unit=noop() effect fn main()->unit=let g=function(f) in g(1)',
            'fn f(x:i64)->i64=x fn main()->i64=let g=function(f) in g("bad")',
            'fn f(x:i64)->i64=x fn main()->i64=let g=function(f) in g(1,2)',
            'fn f(x:i64)->i64=x fn main()->i64=let f=3 in let g=function(f) in g(1)',
            'fn main()->Fn()->i64=function_null()',
        ]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(CheckError):self.program(source)

    def test_bitcasts_are_pure_and_preserve_bits(self):
        p=self.program('fn main()->i64=float_bits(bits_float(-9223372036854775808))')
        self.assertEqual(Reference(p).call('main',[]),-9223372036854775808)

if __name__=='__main__':unittest.main()
