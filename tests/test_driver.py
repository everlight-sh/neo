"""The native neo driver, including installed symlinks and a Python-free PATH."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from neoc.packages import VERSION

ROOT = Path(__file__).resolve().parents[1]


def tools(folder, *names):
    folder.mkdir(exist_ok=True)
    for name in names:
        path = shutil.which(name)
        if path:
            (folder / name).symlink_to(path)
    return folder


def run(argv, cwd, **env):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=180, env=env)


class MissingDriver(unittest.TestCase):
    def test_missing_native_compiler_is_reported_without_starting_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / 'neo'
            shutil.copy2(ROOT / 'neo', launcher)
            python = root / 'python3'
            python.write_text('#!/bin/sh\n: > python-started\n')
            python.chmod(0o755)
            result = run([str(launcher), 'version'], root, PATH=tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn('native neoc executable missing', result.stderr)
            self.assertFalse((root / 'python-started').exists())


class Driver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = Path(os.environ.get('NEOC') or ROOT / '.neo-build/bin/neoc').resolve()
        if not cls.native.is_file():
            raise unittest.SkipTest('set NEOC to a native compiler')

    def test_a_chain_of_symlinks_reaches_the_native_compiler(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'bin').mkdir()
            (tmp / 'lib').mkdir()
            (tmp / 'lib/neo').symlink_to(ROOT / 'neo')
            (tmp / 'bin/neo').symlink_to('../lib/neo')
            path = tools(tmp / 'tools', 'readlink')
            result = run([str(tmp / 'bin/neo'), 'version'], tmp, PATH=str(path), NEOC=str(self.native))
            self.assertEqual((result.returncode, result.stdout.strip()), (0, 'Neo ' + VERSION), result.stderr)

    def test_project_build_and_run_default_to_runtime_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'project with spaces'
            project.mkdir()
            path = tools(Path(tmp) / 'tools', 'clang', 'ld', 'as', 'ld.lld')
            (project / 'neo.toml').write_text('[package]\nentry = "chosen.neo"\n')
            (project / 'chosen.neo').write_text('fn main(n:i64) -> i64 = n+1\n')
            env = dict(PATH=str(path), NEOC=str(self.native), NEO_RUNTIME=str(project / 'missing.o'))
            launcher = str(ROOT / 'neo')
            built = run([launcher, 'build'], project, **env)
            self.assertEqual(built.returncode, 0, (built.stdout, built.stderr))
            result = run([str(project / 'chosen'), '41'], project, **env)
            self.assertEqual((result.returncode, result.stdout), (0, '42\n'), result.stderr)
            result = run([launcher, 'run', '--dev', '--', '41'], project, **env)
            self.assertEqual((result.returncode, result.stdout), (0, '42\n'), result.stderr)

    def test_doctor_reports_missing_clang(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run([str(ROOT / 'neo'), 'doctor'], tmp, PATH=tmp, NEOC=str(self.native))
            self.assertEqual(result.returncode, 1)
            self.assertIn('Clang executable not found', result.stderr)


if __name__ == '__main__':
    unittest.main()
