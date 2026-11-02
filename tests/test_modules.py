import tempfile
import unittest
from pathlib import Path
from neoc import syntax as S
from neoc.modules import sources, SourceError
from neoc.graph import hash_program, program_hash
from neoc.check import Checker, CheckError


class ModuleTests(unittest.TestCase):
    def test_aliases_generic_types_private_declarations_and_ambiguity(self):
        from neoc.reference import Reference
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'a.neo').write_text('private fn secret() -> i64 = 1\nenum Maybe<T> { Nothing, Something(T) }\nfn value() -> Maybe<i64> = Something::<i64>(17)')
            (p/'b.neo').write_text('fn value() -> i64 = 25')
            main=p/'main.neo';main.write_text('import "a.neo" as a import "b.neo" as b fn main() -> i64 = match a::value() { a::Nothing => 0, a::Something(x) => x + b::value() }')
            program=sources(main);hash_program(program);Checker(program).run();self.assertEqual(Reference(program).call('main',[]),42)
            main.write_text('import "a.neo" as a fn main() -> i64 = a::secret()')
            with self.assertRaisesRegex(SourceError,'private'):sources(main)
            main.write_text('import "a.neo" import "b.neo" fn main() -> i64 = 0')
            with self.assertRaisesRegex(SourceError,'ambiguous'):sources(main)

    def test_sealed_records_require_the_declaring_module_for_construction_and_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'lib.neo').write_text('sealed type Valid = { raw: Arr u8 _ } fn valid () -> Valid = Valid { raw = "checked" }')
            main=p/'main.neo'
            main.write_text('import "lib.neo" fn main () -> i64 = len(valid().raw)')
            program=sources(main);hash_program(program);Checker(program).run()
            for expr in ('Valid { raw = "forged" }','valid() with { raw = "forged" }'):
                main.write_text('import "lib.neo" fn main () -> i64 = len(('+expr+').raw)')
                with self.assertRaises(CheckError) as caught:Checker(sources(main)).run()
                self.assertTrue(any('sealed type Valid' in e['msg'] for e in caught.exception.errors))

    def test_sealing_changes_type_hashes(self):
        from neoc.graph import Hasher
        p=S.parse('type Item = { raw: Arr u8 _ } fn main () -> i64 = 0')
        q=S.parse('sealed type Item = { raw: Arr u8 _ } fn main () -> i64 = 0')
        self.assertNotEqual(Hasher({},{'Item':p.types[0]}).ty(S.TRec('Item',()),[]),Hasher({},{'Item':q.types[0]}).ty(S.TRec('Item',()),[]))

    def test_transitive_diamond_and_imported_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'shared.neo').write_text('type Item = { text: Arr u8 _ } fn item () -> Item = Item { text = "hi" }')
            (p/'left.neo').write_text('import "shared.neo" fn left () -> Item = item()')
            (p/'right.neo').write_text('import "shared.neo" fn right () -> i64 = 2')
            (p/'main.neo').write_text('import "left.neo" import "right.neo" fn main () -> i64 = len(left().text) + right()')
            prog=sources(p/'main.neo');hash_program(prog);Checker(prog).run()
            self.assertEqual(len(prog.sources),4)
            self.assertEqual(len(prog.types),1)
            old=program_hash(hash_program(prog))
            (p/'right.neo').write_text('import "shared.neo" fn right () -> i64 = 3')
            self.assertNotEqual(old,program_hash(hash_program(sources(p/'main.neo'))))

    def test_missing_cycle_and_duplicate_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); main=p/'main.neo'; lib=p/'lib.neo'
            main.write_text('import "missing.neo" fn main () -> i64 = 0')
            with self.assertRaisesRegex(SourceError,'No such file'): sources(main)
            main.write_text('import "lib.neo" fn main () -> i64 = 0')
            lib.write_text('import "main.neo"')
            with self.assertRaisesRegex(SourceError,'cyclic'): sources(main)
            lib.write_text('fn main () -> i64 = 1')
            with self.assertRaisesRegex(SourceError,'cannot declare main'): sources(main)

    def test_nested_type_hash_and_recursive_rejection(self):
        a=S.parse('type Inner = { a: i64 } type Outer = { b: Inner } fn main () -> i64 = 0')
        b=S.parse('type Inner = { a: bool } type Outer = { b: Inner } fn main () -> i64 = 0')
        from neoc.graph import Hasher
        self.assertNotEqual(Hasher({}, {x.name:x for x in a.types}).ty(S.TRec('Outer',()),[]),
                            Hasher({}, {x.name:x for x in b.types}).ty(S.TRec('Outer',()),[]))
        p=S.parse('type A = { child: A } fn main () -> i64 = 0')
        with self.assertRaises(CheckError): Checker(p).run()


if __name__=='__main__': unittest.main()
