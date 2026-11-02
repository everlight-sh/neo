"""Compare `neoc modules` with neoc/modules.py on a corpus of Neo sources.

    python3 compiler/tests/modules_differential.py NEOC [--keep DIR] [--show N] [--originals] [--every K] [ROOT ...]

The corpus is that of differential.py. Each case is an entry file: a corpus
file as it is, or a changed copy written beside it, so that its relative
imports and package manifest still apply. The changes provoke the loader's
errors: a missing, cyclic or invalid standard import, a repeated alias, a
repeated declaration, unknown names, and one random deletion and insertion.
--every K changes only every Kth file. Cases that reach a package import,
which the Neo loader does not support yet, and cases on which the Python
loader crashes are counted, not compared.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import differential  # noqa: E402
import modules_dump  # noqa: E402

FN = re.compile(r'^(?:pub |private )?(?:export |extern |cold |inline )*(?:effect(?:\([^)]*\))? )?fn (\w+)', re.M)
IMPORT = re.compile(r'^import [^\n]*\n', re.M)
SELF = '@SELF@'


def variants(label, text):
    """(label, text) cases; SELF in a text stands for the case file's name."""
    yield label, text
    first = IMPORT.search(text)
    if first: yield f'{label}@noimport', text[:first.start()] + text[first.end():]
    yield f'{label}@missing', 'import "neo_missing_module.neo"\n' + text
    yield f'{label}@cycle', f'import "{SELF}"\n' + text
    yield f'{label}@badstd', 'import "std:../io"\n' + text
    yield f'{label}@alias', 'import "std:strings" as twice\nimport "std:option" as twice\n' + text
    name = FN.search(text)
    if name: yield f'{label}@dupdecl', text + f'\nfn {name.group(1)}() -> i64 = 0\n'
    yield f'{label}@value', text + '\nfn neo_probe_value() -> i64 = neo_undefined_value\n'
    yield f'{label}@call', text + '\nfn neo_probe_call() -> i64 = neo_undefined_function(1)\n'
    yield f'{label}@type', text + '\nfn neo_probe_type(x:NeoUndefinedType) -> i64 = 0\n'
    random = [(case, raw.decode()) for case, raw in differential.mutations(label, text) if '@del' in case or '@ins' in case]
    yield from random[:1] + [case for case in random if '@ins' in case[0]][:1]


def compare(job):
    neoc, label, text, keep = job
    source = Path(label.split('#')[0].split('@')[0])
    original = '@' not in label and '#' not in label
    if original: path = source
    else:
        path = source.parent / f'.neodiff-{hashlib.sha256(label.encode()).hexdigest()[:12]}.neo'
        path.write_text(text.replace(SELF, path.name), encoding='utf-8')
    try:
        try: expected = modules_dump.dump(path).encode()
        except (RecursionError, ValueError, IndexError, UnicodeError, TypeError, AttributeError, KeyError, RuntimeError) as exc:
            return 'crash', label, type(exc).__name__
        run = subprocess.run([neoc, 'modules', str(modules_dump.ROOT), str(path)], capture_output=True, timeout=120)
        if run.returncode == 0 and run.stdout.startswith(b'(unsupported'): return 'pkg', label, ''
        if run.returncode == 0 and run.stdout == expected: return 'ok', label, ''
        if keep:
            name = hashlib.sha256(label.encode()).hexdigest()[:12]
            Path(keep, name + '.neo').write_text(text, encoding='utf-8'); Path(keep, name + '.label').write_text(label)
            Path(keep, name + '.py.txt').write_bytes(expected); Path(keep, name + '.neo.txt').write_bytes(run.stdout + run.stderr)
        mine, theirs = run.stdout.split(b'\n'), expected.split(b'\n')
        line = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b), min(len(mine), len(theirs)))
        detail = (f'exit {run.returncode} {run.stderr[-300:]!r}' if run.returncode else
                  f'line {line + 1}\n    neo:    {mine[line][:300] if line < len(mine) else b"<end>"!r}\n'
                  f'    python: {theirs[line][:300] if line < len(theirs) else b"<end>"!r}')
        return 'diff', label, detail
    finally:
        if not original: path.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('neoc'); ap.add_argument('roots', nargs='*'); ap.add_argument('--keep')
    ap.add_argument('--show', type=int, default=20); ap.add_argument('--originals', action='store_true', help='no changed copies')
    ap.add_argument('--every', type=int, default=1, help='change only every Kth file')
    args = ap.parse_intermixed_args()
    if args.keep: os.makedirs(args.keep, exist_ok=True)
    neoc = os.path.abspath(args.neoc)
    jobs = []
    for k, (label, text) in enumerate(differential.sources(args.roots or [differential.REPO])):
        cases = [(label, text)] if args.originals or k % args.every else variants(label, text)
        jobs += [(neoc, case, body, args.keep) for case, body in cases]
    counts = {'ok': 0, 'diff': 0, 'pkg': 0, 'crash': 0}; shown = 0
    with ProcessPoolExecutor() as pool:
        for status, label, detail in pool.map(compare, jobs, chunksize=8):
            counts[status] += 1
            if status == 'diff' and shown < args.show:
                shown += 1; print(f'DIFF {label}: {detail}', flush=True)
    print(f"{len(jobs)} cases: {counts['ok']} match, {counts['diff']} differ, {counts['pkg']} reach a package import, "
          f"{counts['crash']} skipped (Python loader crashed)")
    raise SystemExit(1 if counts['diff'] else 0)


if __name__ == '__main__': main()
