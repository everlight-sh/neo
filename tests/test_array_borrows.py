import unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker
class ArrayBorrows(unittest.TestCase):
    def check(self,source):
        p=S.parse(source);hash_program(p);Checker(p).run();return p
    def test_scalar_result_borrows_do_not_disable_final_mutation_moves(self):
        from neoc.llvm import consume_plan
        p=self.check('fn first(a:Arr i64 n)->i64=if n>0 then a[0] else 0 fn main()->i64=let a=arr(i in 0..2) i in let first_value=first(a) in let b=set(a,0,42) in b[0]+first_value')
        body=p.fns[-1].body;read=body.body.value;self.assertEqual(read.borrowed_args,{0});self.assertTrue(consume_plan([body.body],'a'))
    def test_escaping_effectful_and_move_parameters_remain_consuming(self):
        for declaration,call in [('fn reader(a:Arr i64 n)->Arr i64 _=a','reader(a)'),('effect(fs) fn reader(a:Arr i64 n)->i64=0','reader(a)'),('fn reader(move a:Arr i64 n)->i64=len(a)','reader(a)')]:
            p=self.check(declaration+' effect(fs) fn main()->i64=let a=arr(i in 0..2) i in let result='+call+' in 0');self.assertEqual(p.fns[-1].body.body.value.borrowed_args,set())
if __name__=='__main__':unittest.main()
