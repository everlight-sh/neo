import unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker
from neoc.llvm import field_consume_plan

class FieldMoves(unittest.TestCase):
    def plan(self,tail):
        program=S.parse('type Buffers={left:Arr i64 _,right:Arr i64 _} fn main() -> i64 = let b=Buffers { left=arr(i in 0..2) i,right=arr(i in 0..3) i } in '+tail)
        hash_program(program);Checker(program).run();binding=program.fns[0].body
        return field_consume_plan([binding.body],'b',binding.value.ty)
    def test_disjoint_final_fields_can_move(self):
        plan=self.plan('let left=b.left in let right=b.right in len(left)+len(right)')
        self.assertEqual({name:len(ids) for name,ids in plan.items()},{'left':1,'right':1})
    def test_later_projection_or_whole_value_keeps_required_fields(self):
        plan=self.plan('let left=b.left in let right=b.right in len(left)+len(right)+len(b.left)')
        self.assertFalse(plan['left']);self.assertEqual(len(plan['right']),1)
        plan=self.plan('let left=b.left in let right=b.right in let whole=b in len(left)+len(right)+len(whole.left)')
        self.assertFalse(plan['left']);self.assertFalse(plan['right'])
    def test_reuse_in_one_branch_does_not_block_other_branch(self):
        plan=self.plan('if len(b.left)>0 then let alias=b.left in len(alias)+len(b.left) else let final=b.left in len(final)')
        self.assertEqual(len(plan['left']),1)
    def test_use_after_branch_blocks_both_paths(self):
        plan=self.plan('let alias=if len(b.left)>0 then b.left else b.left in len(alias)+len(b.left)')
        self.assertFalse(plan['left'])
    def test_multiple_escaping_reads_preserve_aliases(self):
        plan=self.plan('let first=b.left in let last=b.left in len(first)+len(last)')
        self.assertFalse(plan['left'])
    def test_repeated_loop_capture_stays_borrowed(self):
        plan=self.plan('let copies=arr(i in 0..3) b.left in len(copies)')
        self.assertFalse(plan['left'])
    def test_record_fields_follow_declared_evaluation_order(self):
        plan=self.plan('let reordered=Buffers {right=b.left,left=b.left} in len(reordered.left)+len(reordered.right)')
        self.assertFalse(plan['left'])
if __name__=='__main__':unittest.main()
