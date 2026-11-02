import unittest
from neoc.syntax import parse
from neoc.graph import hash_program
from neoc.check import Checker
from neoc.kernel_workers import allocation_free


class WorkerSafety(unittest.TestCase):
    def body(self,source,name='candidate'):
        program=parse(source.replace('fn main','fn candidate')+' fn main() -> i64 = 0');hash_program(program);Checker(program).run()
        functions={f.name:f for f in program.fns}
        return functions[name].body,functions

    def test_record_reductions_and_borrowed_arrays_are_safe(self):
        node,fns=self.body('''type Pair={a:f64,b:f64}
fn reduce(a:Arr f64 n) -> Pair = sum(i in 0..n) Pair { a=a[i],b=sqrt(a[i]*a[i]) }
fn main(a:Arr f64 n) -> f64 = let p=reduce(a) in p.a+p.b
''')
        self.assertTrue(allocation_free(node,fns))

    def test_bounded_word_reads_are_allocation_free(self):
        node,fns=self.body('fn main(a:Arr u8 n) -> i64 = sum(i in 0..n) byte_read_le(a,i,1)')
        self.assertTrue(allocation_free(node,fns))
        node,fns=self.body('fn main() -> i64 = byte_read_le(arr(i in 0..8) u8(i),0,8)')
        self.assertFalse(allocation_free(node,fns))

    def test_allocating_owned_effectful_and_managed_projections_stay_private(self):
        for source in [
            'fn main() -> Arr i64 _ = arr(i in 0..4) i',
            'fn main(a:Arr i64 n) -> i64 = len(push(a,1))',
            'type Box={a:Arr i64 _} fn main(a:Box) -> i64 = let child=a.a in len(child)',
            'type Box={a:Arr i64 _} fn own(move a:Box) -> i64 = len(a.a) fn main(a:Box) -> i64 = own(a)',
            'effect fn child() -> i64 = 1 effect fn main() -> i64 = child()',
            'fn child(x:i64) -> i64 = let a=arr(i in 0..2) x+i in sum(i in 0..2) a[i] fn main(x:i64) -> i64 = child(x)',
            'fn child() -> Arr i64 _ = arr(i in 0..4) i fn main() -> i64 = len(child())',
        ]:
            with self.subTest(source=source):
                node,fns=self.body(source);self.assertFalse(allocation_free(node,fns))


if __name__=='__main__':unittest.main()
