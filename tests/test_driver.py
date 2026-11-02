"""The neo driver: reached through symlinks, and clear about Pythons it cannot use."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from neoc.packages import VERSION

ROOT=Path(__file__).resolve().parents[1]


def tools(folder,*names):
    """A PATH directory holding only the named host tools."""
    folder.mkdir(exist_ok=True)
    for name in names:(folder/name).symlink_to(shutil.which(name))
    return folder


def run(argv,cwd,**env):
    return subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=120,env={**os.environ,'PYTHONPATH':'',**env})


class Driver(unittest.TestCase):
    def test_a_chain_of_symlinks_reaches_the_compiler(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);(tmp/'bin').mkdir();(tmp/'lib').mkdir()
            (tmp/'lib/neo').symlink_to(ROOT/'neo');(tmp/'bin/neo').symlink_to('../lib/neo')
            result=run([str(tmp/'bin/neo'),'version'],tmp)
            self.assertEqual((result.returncode,result.stdout.strip()),(0,'Neo '+VERSION),result.stderr)

    def test_neo_python_must_be_recent_enough(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp)/'python';old.write_text('#!/bin/sh\nexit 1\n');old.chmod(0o755)
            result=run([str(ROOT/'neo'),'version'],tmp,NEO_PYTHON=str(old))
            self.assertEqual(result.returncode,1);self.assertIn('is not Python 3.11 or newer',result.stderr)

    def test_without_a_recent_python_it_names_the_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=tools(Path(tmp)/'bin','dirname','readlink','uname')
            (path/'python3').write_text('#!/bin/sh\n[ "$1" = --version ] && echo "Python 3.9.6" && exit 0\nexit 1\n');(path/'python3').chmod(0o755)
            result=run(['/bin/sh',str(ROOT/'neo'),'version'],tmp,PATH=str(path))
            self.assertEqual(result.returncode,1)
            self.assertIn('needs Python 3.11 or newer (Python 3.9.6)',result.stderr);self.assertIn('install it with',result.stderr)

    def test_doctor_names_missing_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=tools(Path(tmp)/'bin','dirname','readlink','uname')
            result=run([str(ROOT/'neo'),'doctor'],tmp,PATH=str(path),NEO_PYTHON=sys.executable)
            self.assertEqual(result.returncode,1,result.stdout)
            self.assertRegex(result.stdout,r'missing +clang');self.assertRegex(result.stdout,r'missing +linker')
            self.assertIn('Install the missing tools with:',result.stdout);self.assertNotIn('built and ran',result.stdout)


if __name__=='__main__':unittest.main()
