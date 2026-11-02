import random,unittest
from neoc import syntax as S
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.reference import Reference,Fault
from neoc.fold import Interp,Unfoldable
class ByteWrites(unittest.TestCase):
    def test_oracles_and_value_semantics(self):
        p=S.parse('fn write(a:Arr u8 _,at:i64,v:i64,w:i64)->Arr u8 _=byte_write_le(a,at,v,w) fn copy(a:Arr u8 _,at:i64,b:Arr u8 _)->Arr u8 _=byte_copy(a,at,b) fn main()->i64=0')
        hash_program(p);Checker(p).run();rng=random.Random(26026)
        for _ in range(500):
            a=[rng.randrange(256) for _ in range(rng.randrange(30))];at=rng.randrange(-2,35);w=rng.randrange(-2,11);v=rng.randrange(-(1<<63),(1<<63));b=[rng.randrange(256) for _ in range(rng.randrange(12))]
            for fn,args,width,data in [(p.fns[0],[a,at,v,w],w,[(v>>(8*i))&255 for i in range(max(0,w))]),(p.fns[1],[a,at,b],len(b),b)]:
                valid=0<=at<=len(a) and 0<=width<=len(a)-at and (fn.name=='copy' or w<=8)
                env={x.name:y for x,y in zip(fn.params,args)};original=a.copy()
                if valid:
                    expected=a[:at]+data+a[at+width:]
                    self.assertEqual(Reference(p).call(fn.name,args),expected)
                    self.assertEqual(Interp({f.name:f for f in p.fns}).ev(fn.body,env),expected)
                else:
                    with self.assertRaises(Fault):Reference(p).call(fn.name,args)
                    with self.assertRaises(Unfoldable):Interp({f.name:f for f in p.fns}).ev(fn.body,env)
                self.assertEqual(a,original)
if __name__=='__main__':unittest.main()
