"""Compare native and reference project tests, with a Python-free native PATH."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = '''[package]
name = "test-project"
version = "0.1.0"

[tool.neo]
doc-tests = ["docs/*.md"]
test-globs = ["tests/**/[ab]*_test.neo", "tests/*_test.ax"]

[[test]]
name = "args-and-env"
file = "args.neo"
args = [41]
exit = 7
stdout = "42:hello:2\\n"
[test.env]
CASE_WORD = "hello"
NEO_THREADS = "2"

[[test]]
name = "rejected"
file = "reject.neo"
reject = true
diagnostic = "division"

[[test]]
name = "large-output"
file = "large.neo"
'''


def setup(project):
    (project / 'docs').mkdir(parents=True)
    (project / 'tests/nested').mkdir(parents=True)
    manifest = project / 'neo.toml'
    manifest.write_text(MANIFEST + 'stdout = ' + json.dumps('x' * 9000) + '\n')
    (project / 'args.neo').write_text(
        'import "std:io"\nimport "std:strings"\n'
        'effect fn main(n:i64) -> unit = let wrote=print_out(concat(int_text(n+1),":",'
        'env_get("CASE_WORD").value,":",env_get("NEO_THREADS").value,"\\n")) in process_exit(7)\n'
    )
    (project / 'reject.neo').write_text('fn main(n:i64) -> i64 = 42/n\n')
    (project / 'large.neo').write_text("fn main() -> Arr u8 _ = arr(i in 0..9000) 'x'\n")
    (project / 'docs/a.md').write_text(
        '```neo\nfn main() -> i64 = 42\n```\n\n```text\n42\n```\n'
        '\n```axon\nfn main() -> Arr u8 _ = "legacy\\n"\n```\n```text\nlegacy\n```\n'
        '\n```neo\nThis unpaired fence is skipped.\n```\n'
    )
    (project / 'tests/nested/b_test.neo').write_text('fn test_two() -> bool = true\n')
    (project / 'tests/a_test.neo').write_text(
        'fn test_one() -> bool = true\nfn test_also() -> bool = 1<2\n'
    )
    (project / 'tests/legacy_test.ax').write_text('fn test_legacy() -> bool = true\n')
    (project / 'tests/ignored_test.neo').write_text('fn test_ignored() -> bool = false\n')
    (project / 'tests/b_empty_test.neo').write_text('fn helper() -> bool = false\n')
    for i in range(1000):
        (project / f'tests/ignored-directory-entry-{i:04}.txt').touch()
    return manifest


def run(command, project, env):
    return subprocess.run(command, cwd=project, env=env, text=True,
                          capture_output=True, timeout=240)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('neoc', type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='neo-test-diff-') as temporary:
        root = Path(temporary)
        project = root / 'project with spaces'
        manifest = setup(project)
        tools = root / 'toolchain'
        tools.mkdir()
        for tool in ('clang', 'ld', 'as', 'ld.lld'):
            path = shutil.which(tool)
            if path:
                (tools / tool).symlink_to(path)
        prefix = '/bin/sh -c \'exec "$@"\' native-runner'
        env = {'PATH': str(tools), 'NEOC': str(args.neoc.resolve()), 'NEO_RUNTIME': str(root / 'missing.o'),
               'NEO_THREADS': '9', 'NEO_RUNNER': prefix}
        reference = {**os.environ, 'NEO_THREADS': '9', 'NEO_RUNNER': prefix}
        native_cmd = [ROOT / 'neo', 'test']
        reference_cmd = [ROOT / 'neoc.sh', 'test']
        python = run([*reference_cmd, manifest, '--unit-only'], root, reference)
        native = run([*native_cmd, manifest, '--unit-only'], root, env)
        assert python.returncode == native.returncode == 0, (python, native)
        assert python.stdout == native.stdout and not native.stderr, (python, native)
        assert native.stdout.splitlines() == [
            'PASS args-and-env', 'PASS rejected', 'PASS large-output', 'PASS doc-a-0', 'PASS doc-a-1',
            'PASS tests/a_test.neo', 'PASS tests/nested/b_test.neo', 'PASS tests/legacy_test.ax',
            'neo test: 8 native cases, 0 failed',
        ], native
        assert not list(project.glob('.neo-test-*'))

        manifest.write_text('''[tool.neo]
test-globs = []
integration = "must-not-run.py"

[[test]]
name = "timeout"
file = "sleep.neo"
timeout = 0.05

[[test]]
name = "stdout"
file = "large.neo"
stdout = "wrong"

[[test]]
name = "compile"
file = "reject.neo"

[[test]]
name = "following"
file = "large.neo"
''')
        (project / 'sleep.neo').write_text(
            'import "std:time"\neffect fn main() -> unit = let waited=sleep_ms(1000) in noop()\n'
        )
        python = run([*reference_cmd, '--unit-only'], project, reference)
        native = run([*native_cmd, '--unit-only'], project, env)
        assert python.returncode == native.returncode == 1, (python, native)
        assert native.stdout == python.stdout == 'PASS following\nneo test: 4 native cases, 3 failed\n', (python, native)
        assert 'FAIL timeout timed out after 50 ms' in native.stderr, native
        assert 'FAIL stdout stdout differs' in native.stderr, native
        assert 'FAIL compile build failed' in native.stderr, native
        assert 'skipped Python reference hooks' not in native.stderr, native
        assert not list(project.glob('.neo-test-*'))
        native = run([*native_cmd], project, env)
        assert native.returncode == 1 and 'skipped Python reference hooks' in native.stderr, native
        assert not list(project.glob('.neo-test-*'))
    print('Native test discovery, execution, failure reporting, and cleanup matched the reference on a Python-free PATH')


if __name__ == '__main__':
    main()
