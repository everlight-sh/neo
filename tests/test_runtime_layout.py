import unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker
from neoc.llvm import LLVMGen
class RuntimeLayout(unittest.TestCase):
 def test_freestanding_state_alignment_by_target(self):
  for triple,alignment in [('x86_64-unknown-linux-gnu',4096),('aarch64-unknown-linux-gnu',16),('arm64-apple-darwin',16)]:
   with self.subTest(triple=triple):
    p=S.parse('fn main()->i64=0');h=hash_program(p);Checker(p).run();ir=LLVMGen(p.fns,h,triple).program()
    self.assertIn(f'@ax_runtime_state = internal global [256 x i64] zeroinitializer, align {alignment}',ir)
if __name__=='__main__':unittest.main()
