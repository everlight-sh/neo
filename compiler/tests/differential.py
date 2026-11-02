"""Compare the Neo front end with neoc's parser on a corpus of Neo sources.

    python3 compiler/tests/differential.py NEOC [--keep DIR] [ROOT ...]

NEOC is the built compiler/src/main.neo. The corpus is every .neo/.ax file
under the roots (default: this repository), every ```neo or ```axon block in
their Markdown, and mutated copies of each file: truncations, one deleted or
inserted character, and CRLF line endings. Mutations reach the parser's
error paths. Both dumps must match byte for byte. Inputs on which the Python
parser crashes instead of reporting a syntax error are skipped and counted.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ast_dump  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SKIP_DIRS = {'.git', 'node_modules', '.neo-build', '.axon-build', '.kernel-build', '__pycache__', 'results', 'target', 'build'}
FENCE = re.compile(r'```(?:neo|axon)\n(.*?)```', re.S)
INSERTS = ['(', ')', '{', '}', ',', '=', 'in', ' let ', '"', "'", '\\', '::', '<', '..', '?', '@', 'é', '​']


def sources(roots):
    for root in roots:
        for path in sorted(Path(root).rglob('*')):
            if any(part in SKIP_DIRS for part in path.parts) or not path.is_file(): continue
            if path.suffix in ('.neo', '.ax', '.md'):
                try: text = path.read_text(encoding='utf-8')
                except (OSError, UnicodeError): continue
                if path.suffix == '.md':
                    for k, block in enumerate(FENCE.findall(text)): yield f'{path}#{k}', block
                else: yield str(path), text


def mutations(label, text):
    """(label, raw bytes) cases: the source, then mutated copies."""
    yield label, text.encode()
    rng = random.Random(hashlib.sha256(label.encode()).digest())
    n = len(text)
    if n == 0: return
    for k in range(1, 7): yield f'{label}@cut{k}', text[:n * k // 7].encode()
    for k in range(4):
        at = rng.randrange(n)
        yield f'{label}@del{at}', (text[:at] + text[at + 1:]).encode()
        at = rng.randrange(n + 1); piece = rng.choice(INSERTS)
        yield f'{label}@ins{at}', (text[:at] + piece + text[at:]).encode()
    if rng.random() < 0.2: yield f'{label}@crlf', text.replace('\n', '\r\n').encode()


def compare(job):
    neoc, label, raw, keep = job
    with tempfile.NamedTemporaryFile(suffix='.neo', delete=False) as file: file.write(raw); path = file.name
    try:
        try: expected = ast_dump.dump(Path(path).read_text(encoding='utf-8')).encode()
        except (RecursionError, ValueError, IndexError, UnicodeError, TypeError) as exc:
            return 'skip', label, type(exc).__name__
        run = subprocess.run([neoc, 'parse', path], capture_output=True, timeout=60)
        if run.returncode == 0 and run.stdout == expected: return 'ok', label, ''
        if keep:
            name = hashlib.sha256(label.encode()).hexdigest()[:12]
            Path(keep, name + '.neo').write_bytes(raw); Path(keep, name + '.py.txt').write_bytes(expected)
            Path(keep, name + '.neo.txt').write_bytes(run.stdout + run.stderr)
        mine, theirs = run.stdout.split(b'\n'), expected.split(b'\n')
        line = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b), min(len(mine), len(theirs)))
        detail = (f'exit {run.returncode} {run.stderr[-300:]!r}' if run.returncode else
                  f'line {line + 1}\n    neo:    {mine[line][:300] if line < len(mine) else b"<end>"!r}\n'
                  f'    python: {theirs[line][:300] if line < len(theirs) else b"<end>"!r}')
        return 'diff', label, detail
    finally: os.unlink(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('neoc'); ap.add_argument('roots', nargs='*'); ap.add_argument('--keep')
    ap.add_argument('--show', type=int, default=20); ap.add_argument('--originals', action='store_true', help='no mutations')
    args = ap.parse_intermixed_args()
    if args.keep: os.makedirs(args.keep, exist_ok=True)
    neoc = os.path.abspath(args.neoc)
    jobs = []
    for label, text in sources(args.roots or [REPO]):
        cases = [(label, text.encode())] if args.originals else mutations(label, text)
        jobs += [(neoc, case, raw, args.keep) for case, raw in cases]
    counts = {'ok': 0, 'diff': 0, 'skip': 0}; shown = 0
    with ProcessPoolExecutor() as pool:
        for status, label, detail in pool.map(compare, jobs, chunksize=16):
            counts[status] += 1
            if status == 'diff' and shown < args.show:
                shown += 1; print(f'DIFF {label}: {detail}')
    print(f"{len(jobs)} cases: {counts['ok']} match, {counts['diff']} differ, {counts['skip']} skipped (Python parser crashed)")
    raise SystemExit(1 if counts['diff'] else 0)


if __name__ == '__main__': main()
