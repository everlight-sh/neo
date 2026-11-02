import unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.llvm import LLVMGen

class PushGrowth(unittest.TestCase):
    def emit(self,source):
        program=S.parse(source);hashes=hash_program(program);Checker(program).run()
        return LLVMGen(program.fns,hashes,'aarch64-unknown-linux-gnu').program()
    def test_power_of_two_sized_elements_do_not_round_capacity_per_push(self):
        for typ,value in [('i64','7'),('i32','i32(7)'),('u8','u8(7)'),('bool','true')]:
            ir=self.emit(f'fn main(n:i64{{n>=0}})->i64=let row=push(arr(i in 0..n) {value},{value}) in len(row)')
            self.assertNotIn('call i64 @llvm.ctlz',ir)
            self.assertIn('push_inplace',ir);self.assertIn('push_allocate',ir)
    def test_nested_array_descriptors_keep_rounded_byte_capacity(self):
        ir=self.emit('fn empty()->Arr Arr u8 _ _=arr(i in 0..0) "" fn main()->i64=len(push(empty(),"payload"))')
        self.assertIn('call i64 @llvm.ctlz',ir)
    def test_record_arrays_preserve_soa_reallocation(self):
        ir=self.emit('type Pair={first:i64,second:i64} fn main(n:i64{n>=0})->i64=len(push(arr(i in 0..n) Pair {first=i,second=7*i},Pair {first=1,second=2}))')
        self.assertNotIn('push_inplace',ir);self.assertIn('push_allocate',ir)
    def test_capacity_boundary_equivalence_through_maximum_allocation(self):
        for size in [1,2,4,8,16]:
            for power in range(63):
                for length in [max(0,2**power-1),2**power,2**power+1]:
                    needed=(length+1)*size
                    if needed>2**62:continue
                    rounded=max(16,1<<((max(1,length*size)-1).bit_length()))
                    fits=length<16//size or bool(length&(length-1))
                    self.assertEqual(fits,needed<=rounded,(size,length))
if __name__=='__main__':unittest.main()
