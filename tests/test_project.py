import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from neoc.project import formatted, init, manifest

class ProjectTests(unittest.TestCase):
    def test_format_preserves_tokens_and_is_idempotent(self):
        source='; comment  \nfn main () -> Arr u8 _ = "a  b\\n"   \n\n\n\n'
        result=formatted(source)
        self.assertEqual(formatted(result),result)
        self.assertIn('"a  b\\n"',result)
        self.assertFalse(result.endswith('\n\n'))
    def test_init_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sample';init(Namespace(path=str(path)))
            root,data=manifest(path)
            self.assertEqual(data['package']['entry'],'src/main.neo')
            self.assertTrue((root/'src/main.neo').is_file())
            with self.assertRaises(ValueError):init(Namespace(path=str(path)))
    def test_format_generic_scopes_operators_and_comments(self):
        source='fn id<T>(x:T)->T=x ; keep this\nfn main()->i64=let x=id::<i64>(-7) in x+9\n'
        result=formatted(source)
        self.assertIn('id<T>(x: T) -> T = x  ; keep this',result)
        self.assertIn('x + 9',result)
        self.assertEqual(result,formatted(result))
        self.assertEqual(formatted('fn main()->Arr u8 _="a\nb"\n'),'fn main()->Arr u8 _="a\nb"\n')

if __name__=='__main__':unittest.main()
