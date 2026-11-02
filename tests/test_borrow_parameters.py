import unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker, CheckError
from neoc.llvm import consume_plan

class BorrowParameters(unittest.TestCase):
    def checked(self,source):
        program=S.parse(source);hash_program(program);Checker(program).run();return program
    def test_effect_calls_borrow_explicit_parameters(self):
        p=self.checked('effect(fs) fn size(borrow a:Arr i64 n)->i64=n effect(fs) fn main()->i64=let a=arr(i in 0..2) i in size(a)')
        self.assertTrue(p.fns[0].params[0].borrowed)
        self.assertEqual(p.fns[-1].body.body.borrowed_args,{0})
    def test_borrow_remains_an_identifier(self):
        p=self.checked('fn identity(borrow:i64)->i64=borrow fn main()->i64=let borrow=4 in identity(borrow)')
        self.assertFalse(p.fns[0].params[0].borrowed)
    def test_live_call_borrow_blocks_overlapping_move(self):
        p=self.checked('effect(fs) fn use(borrow a:Arr i64 _,move b:Arr i64 _)->i64=len(a)+len(b) effect(fs) fn main()->i64=let a=arr(i in 0..2) i in use(a,a)')
        self.assertFalse(consume_plan([p.fns[-1].body.body],'a'))
    def test_contract_changes_content_hash(self):
        a=S.parse('effect(fs) fn size(a:Arr i64 n)->i64=n');b=S.parse('effect(fs) fn size(borrow a:Arr i64 n)->i64=n')
        hash_program(a);hash_program(b);self.assertNotEqual(a.fns[0].hash,b.fns[0].hash)
    def test_reject_scalar_borrows_and_erased_callback_contracts(self):
        for source in ['fn f(borrow value:i64)->i64=value fn main()->i64=0',
                       'fn f(borrow value:Arr i64 _)->i64=len(value) fn main()->i64=let callback=function(f) in 0']:
            with self.subTest(source=source),self.assertRaises(CheckError):self.checked(source)
    def test_reject_conflicting_modifiers(self):
        with self.assertRaises(S.SyntaxError_):S.parse('fn f(move borrow a:Arr i64 _)->i64=len(a)')

if __name__=='__main__':unittest.main()
