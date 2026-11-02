import random,unittest
from neoc import syntax as S
from neoc.graph import hash_program
from neoc.check import Checker,CheckError
from neoc.reference import Reference
from neoc.fold import Interp
class ByteEqual(unittest.TestCase):
    def test_value_oracles(self):
        p=S.parse('fn equal(a:Arr u8 _,b:Arr u8 _)->bool=byte_equal(a,b) fn main()->i64=0');hash_program(p);Checker(p).run();rng=random.Random(261031)
        for _ in range(1200):
            a=[rng.randrange(256) for _ in range(rng.randrange(100))];b=a.copy() if rng.randrange(2) else [rng.randrange(256) for _ in range(rng.randrange(100))]
            if b and rng.randrange(3)==0:b[rng.randrange(len(b))]^=1
            self.assertEqual(Reference(p).call('equal',[a,b]),a==b)
            self.assertEqual(Interp({f.name:f for f in p.fns}).ev(p.fns[0].body,{'a':a,'b':b}),a==b)
    def test_signature(self):
        for args in ['', '"a"', '"a",1', '1,2', '"a","b","c"']:
            p=S.parse('fn main()->bool=byte_equal('+args+')');hash_program(p)
            with self.assertRaises(CheckError):Checker(p).run()
if __name__=='__main__':unittest.main()
