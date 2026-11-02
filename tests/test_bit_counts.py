import random,unittest
from neoc import syntax as S
from neoc.check import Checker,CheckError
from neoc.graph import hash_program
from neoc.reference import Reference
from neoc.fold import Interp
class BitCounts(unittest.TestCase):
    def test_ctz(self):
        p=S.parse('fn bits(x:i64)->i64=count_trailing_zeros(x) fn main()->i64=0');hash_program(p);Checker(p).run()
        rng=random.Random(602627)
        for value in [0,-1,-2**63,2**63-1]+[1<<i for i in range(63)]+[-(1<<i) for i in range(64)]+[rng.randrange(-2**63,2**63) for _ in range(400)]:
            raw=value%(1<<64);want=64 if raw==0 else len(bin(raw))-len(bin(raw).rstrip('0'))
            self.assertEqual(Reference(p).call('bits',[value]),want)
            self.assertEqual(Interp({f.name:f for f in p.fns}).ev(p.fns[0].body,{'x':value}),want)
    def test_signature(self):
        for args in ['', '1,2', 'true','1.5']:
            p=S.parse('fn main()->i64=count_trailing_zeros('+args+')');hash_program(p)
            with self.assertRaises(CheckError):Checker(p).run()
if __name__=='__main__':unittest.main()
