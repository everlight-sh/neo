import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.llvm import LLVMGen

class WordBytes(unittest.TestCase):
    def emit(self,body,lo='0'):
        # Exercise the reachable sequential path; a pure main uses its
        # parallel variant and previously left this optimized body dead.
        program=S.parse('effect fn main(word:i64,n:i64{n>=0 && n<=1024})->Arr u8 _=arr(i in '+lo+'..n) '+body)
        hashes=hash_program(program);Checker(program).run()
        return LLVMGen(program.fns,hashes,'aarch64-unknown-linux-gnu').program()
    def test_short_little_endian_store_has_guard_and_fallback(self):
        ir=self.emit('u8(shift_right(word,i*8))')
        self.assertIn('word_bytes',ir);self.assertIn('byte_loop',ir)
        self.assertIn('bytes_ready',ir);self.assertIn(', align 1',ir)
        self.assertIn('icmp sle i64',ir)
    def test_other_comprehensions_keep_element_loop(self):
        for body,lo in [('u8(shift_right(i,i*8))','0'),('u8(shift_right(word,i*7))','0'),('u8(shift_right(word,i*8))','1')]:
            self.assertNotIn('word_bytes',self.emit(body,lo))
if __name__=='__main__':unittest.main()
