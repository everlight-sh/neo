import random,unittest
from neoc import syntax as S
from neoc.check import Checker,CheckError
from neoc.graph import hash_program
from neoc.reference import Reference,Fault
from neoc.fold import Interp,Unfoldable
class ByteReads(unittest.TestCase):
    def test_independent_values_and_invalid_ranges(self):
        p=S.parse('fn read(a:Arr u8 _,at:i64,w:i64)->i64=byte_read_le(a,at,w) fn main()->i64=0');hash_program(p);Checker(p).run();rng=random.Random(271027)
        fixtures=[([255]*8,0,8),([0]*8,0,8),([0]*7+[128],0,8),([255]*7+[127],0,8)]
        fixtures += [([rng.randrange(256) for _ in range(rng.randrange(100))],rng.choice([-2**63,2**63-1,rng.randrange(-2,105)]),rng.randrange(-1,11)) for _ in range(2200)]
        fixtures += [([rng.randrange(256) for _ in range(100)],at,w) for w in [1,2,4,8] for at in range(93)]
        f=p.fns[0];interp=Interp({f.name:f for f in p.fns})
        for value,at,width in fixtures:
            env={'a':value,'at':at,'w':width};original=value.copy()
            if width in (1,2,4,8) and 0<=at<=len(value)-width:
                want=int.from_bytes(bytes(value[at:at+width]),'little',signed=width==8)
                self.assertEqual(Reference(p).call('read',[value,at,width]),want)
                self.assertEqual(interp.ev(f.body,env),want)
            else:
                with self.assertRaises(Fault):Reference(p).call('read',[value,at,width])
                with self.assertRaises(Unfoldable):interp.ev(f.body,env)
            self.assertEqual(value,original)
    def test_signature(self):
        for args in ['', '"x"', '"x",0', '0,0,1', '"x",true,1','"x",0,1.0','"x",0,1,2','arr(i in 0..8) i,0,8']:
            p=S.parse('fn main()->i64=byte_read_le('+args+')');hash_program(p)
            with self.assertRaises(CheckError):Checker(p).run()
if __name__=='__main__':unittest.main()
