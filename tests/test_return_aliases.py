import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.return_aliases import summaries

class ReturnAliases(unittest.TestCase):
    def analyze(self,source):
        program=S.parse(source+' fn main()->i64=0');hash_program(program);Checker(program).run()
        return summaries(program.fns)
    def test_copied_bytes_do_not_escape(self):
        got=self.analyze('fn copy(a:Arr u8 n)->Arr u8 _=arr(i in 0..n) a[i] fn wrap(a:Arr u8 n)->Arr u8 _=copy(a)')
        self.assertEqual(got['copy'],set());self.assertEqual(got['wrap'],set())
    def test_aliases_survive_calls_slices_and_records(self):
        got=self.analyze('type Box={value:Arr u8 _} fn identity(a:Arr u8 _)->Arr u8 _=a fn tail(a:Arr u8 n)->Arr u8 _=byte_slice(a,0,n) fn boxed(a:Arr u8 _)->Box=Box{value=identity(a)}')
        for name in ['identity','tail','boxed']:self.assertEqual(got[name],{0})
    def test_concat_copies_only_later_arguments(self):
        got=self.analyze('fn join(a:Arr u8 _,b:Arr u8 _)->Arr u8 _=concat(a,b)')
        self.assertEqual(got['join'],{0})
    def test_set_and_push_can_store_a_new_child_alias(self):
        got=self.analyze('fn replace(a:Arr Arr u8 _ n,b:Arr u8 _)->Arr Arr u8 _ _=check n>0 in set(a,0,b) fn append(a:Arr Arr u8 _ _,b:Arr u8 _)->Arr Arr u8 _ _=push(a,b)')
        for name in ['replace','append']:self.assertEqual(got[name],{0,1})
    def test_loop_backedges_carry_aliases(self):
        got=self.analyze('fn looped(a:Arr u8 _,b:Arr u8 _,n:i64{n>=0})->Arr u8 _=loop(i=0,out=a) while i<n next(i+1,b) yield out')
        self.assertEqual(got['looped'],{0,1})
    def test_effects_and_indirect_calls_are_opaque(self):
        got=self.analyze('effect(fs) fn effectful(a:Arr u8 _)->Arr u8 _=a fn indirect(f:Fn(Arr u8 _)->Arr u8 _,a:Arr u8 _)->Arr u8 _=f(a)')
        for name in ['effectful','indirect']:self.assertIn(-1,got[name]);self.assertIn(0 if name=='effectful' else 1,got[name])
    def test_mutual_recursion_never_assumes_no_alias(self):
        got=self.analyze('fn left(a:Arr u8 _,n:i64)->Arr u8 _=if n==0 then a else right(a,n-1) fn right(a:Arr u8 _,n:i64)->Arr u8 _=if n==0 then a else left(a,n-1)')
        self.assertEqual(got['left'],{0});self.assertEqual(got['right'],{0})

if __name__=='__main__':unittest.main()
