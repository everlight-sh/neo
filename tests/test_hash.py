import json
from pathlib import Path
import tempfile
import unittest
from neoc.modules import sources
from neoc.check import Checker
from neoc.graph import hash_program
from neoc.reference import Reference


class HashVectors(unittest.TestCase):
    def test_all_64_published_siphash_24_vectors(self):
        vectors=json.loads((Path(__file__).parent/'fixtures/siphash_vectors.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'main.neo';source.write_text('import "std:hash" fn main() -> i64 = 0')
            p=sources(source);hash_program(p);Checker(p).run()
        reference=Reference(p,budget=10000000)
        key=bytes.fromhex(vectors['key']);seed0=int.from_bytes(key[:8],'little');seed1=int.from_bytes(key[8:],'little')
        for n,expected in enumerate(vectors['vectors']):
            with self.subTest(length=n):self.assertEqual(reference.call('hash_bytes',[list(range(n)),seed0,seed1])%(1<<64),int(expected,16))


if __name__=='__main__':unittest.main()
