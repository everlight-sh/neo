import json
from pathlib import Path
import tempfile
import unittest
from neoc import packages
from neoc.modules import sources, SourceError
from neoc.check import Checker
from neoc.graph import hash_program, program_hash
from neoc.reference import Reference


class Packages(unittest.TestCase):
    def setup_tree(self,base):
        app=base/'app';lib=base/'library'
        for p in (app,lib):(p/'src').mkdir(parents=True)
        (lib/'neo.toml').write_text('[package]\nname="math"\nversion="1.2.3"\nentry="src/lib.neo"\n')
        (lib/'src/lib.neo').write_text('private fn hidden() -> i64 = 99\nfn answer() -> i64 = 42\n')
        (app/'neo.toml').write_text('[package]\nname="app"\nversion="0.1.0"\n[dependencies]\nmath={path="../library",version="1.2.3"}\n')
        (app/'src/main.neo').write_text('import "pkg:math" as math\nfn main() -> i64 = math::answer()\n')
        return app,lib

    def test_lock_tamper_detection_and_offline_vendor(self):
        with tempfile.TemporaryDirectory() as tmp:
            app,lib=self.setup_tree(Path(tmp));a=packages.write(app)
            self.assertEqual(a,packages.write(app));self.assertEqual(len(a['packages']),2)
            main=app/'src/main.neo';main.write_text(main.read_text()+'; root development does not require relocking\n');packages.verify(app)
            p=sources(app/'src/main.neo');hash_program(p);Checker(p).run();self.assertEqual(Reference(p).call('main',[]),42)
            source=lib/'src/lib.neo';old=source.read_text();source.write_text(old+'; changed\n')
            with self.assertRaisesRegex(ValueError,'source changed'):packages.verify(app)
            source.write_text(old);packages.vendor(app)
            import shutil
            shutil.rmtree(lib)
            self.assertEqual(packages.verify(app)['root'],'app@0.1.0')
            p=sources(app/'src/main.neo');hash_program(p);Checker(p).run();self.assertEqual(Reference(p).call('main',[]),42)

    def test_exact_versions_cycles_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            app,lib=self.setup_tree(Path(tmp));manifest=lib/'neo.toml';old=manifest.read_text()
            manifest.write_text(old.replace('1.2.3','1.2.4'))
            with self.assertRaisesRegex(ValueError,'version mismatch'):packages.write(app)
            manifest.write_text(old+'[dependencies]\napp={path="../app",version="0.1.0"}\n')
            with self.assertRaisesRegex(ValueError,'cyclic'):packages.write(app)
            manifest.write_text(old);packages.write(app)
            for name in ('pkg:math/../secret','pkg:unknown','pkg:math//a','pkg:math/./a'):
                with self.subTest(name=name),self.assertRaises(ValueError):packages.resolve_import(name,app/'src/main.neo',app)

    def test_relocation_has_same_graph(self):
        hashes=[]
        with tempfile.TemporaryDirectory() as first,tempfile.TemporaryDirectory() as second:
            for root in (first,second):
                app,lib=self.setup_tree(Path(root));packages.write(app)
                hashes.append(program_hash(hash_program(sources(app/'src/main.neo'))))
            self.assertEqual(*hashes)

    def test_malformed_lock_and_metadata_are_normal_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            app,lib=self.setup_tree(Path(tmp))
            for value in ([],{}, {'format':1,'root':'app@0.1.0','packages':{'app@0.1.0':{}}}):
                (app/'neo.lock').write_text(json.dumps(value))
                with self.assertRaises(ValueError):packages.verify(app)
            (lib/'neo.toml').write_text('[package]\nname=7\nversion="1.2.3"\n')
            with self.assertRaisesRegex(ValueError,'name'):packages.write(app)


if __name__=='__main__':unittest.main()
