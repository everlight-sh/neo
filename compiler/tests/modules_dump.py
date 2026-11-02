"""Canonical dump of a program as neoc/modules.py loads it: the reference for
`neoc modules ROOT FILE` (compiler/src/modules.neo), where ROOT is this
repository. The two must match byte for byte. The runtime files are x86-64
Linux's.

    python3 compiler/tests/modules_dump.py FILE

A failure to read a file prints as `cannot read PATH`, as Neo words it,
instead of Python's exception text.
"""
import functools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
import ast_dump  # noqa: E402
from neoc import modules as M, syntax as S  # noqa: E402

RUNTIME = ['core.neo', 'platform_linux_x86_64.neo', 'http.neo', 'handles.neo', 'http_linux.neo', 'http_uring.neo']
# The same text always lexes to the same tokens, which nothing changes.
S.lex = functools.lru_cache(maxsize=512)(S.lex)


def read_failure(exc):
    """The path whose reading raised exc's cause, or None for other errors."""
    cause = exc.__cause__
    if isinstance(cause, OSError): return cause.filename
    if isinstance(cause, UnicodeError):
        tb = cause.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_name == 'visit': return tb.tb_frame.f_locals['path']
            tb = tb.tb_next
    return None


def pairs(names): return '(' + ' '.join(f'({k} {v})' for k, v in sorted(names.items())) + ')'


def dump(entry):
    entry = Path(entry).resolve()
    try: program = M.sources(entry, [ROOT / 'runtime' / name for name in RUNTIME])
    except M.SourceError as exc:
        d = exc.diagnostic; failed = read_failure(exc)
        return f"(error {d['file']} {d['pos'][0]}:{d['pos'][1]} {d['msg'] if failed is None else f'cannot read {failed}'})\n"
    lines = []
    for p in program.sources:
        path = Path(p)
        trusted = path.is_relative_to(M.STDLIB) or path.is_relative_to(M.RUNTIME)
        prefix = '-' if trusted else '__m' + M._identity(path, entry) + '_'
        lines.append(f"(module {p} {prefix} ({' '.join(program.dependencies[p])}))")
    lines.append(f'(surface {entry} {pairs(program.module_symbols[str(entry)])})')
    lines.append(f'(scope {pairs(program.entry_scope)})')
    for d in program.types: lines += [f'(decl {d.source} {d.display_name})', ast_dump.type_decl(d)]
    for f in program.fns: lines += [f'(decl {f.source} {f.display_name})', ast_dump.fn_decl(f)]
    return ''.join(line + '\n' for line in lines)


if __name__ == '__main__': sys.stdout.buffer.write(dump(sys.argv[1]).encode('utf-8'))
