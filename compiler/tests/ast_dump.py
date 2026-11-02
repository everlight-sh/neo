"""Canonical dump of neoc's parse of a file: the reference for `neoc parse FILE`
from the Neo front end (compiler/src/dump.neo). The two must match byte for byte.

    python3 compiler/tests/ast_dump.py FILE
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from neoc import syntax as S  # noqa: E402

SCALARS = {S.TInt: 'i64', S.TFloat: 'f64', S.TBool: 'bool', S.TByte: 'u8', S.TU16: 'u16',
           S.TInt32: 'i32', S.TPtr: 'ptr', S.TUnit: 'unit'}


def pos(node): return f' {node.pos[0]}:{node.pos[1]}'
def names(items): return '(' + ' '.join(items) + ')'
def exprs(items): return '(' + ' '.join(expr(e) for e in items) + ')'
def types(items): return '(' + ' '.join(ty(t) for t in items) + ')'
def inits(fields): return '(' + ' '.join(f'({n} {expr(e)})' for n, e in fields) + ')'


def ty(t):
    if type(t) in SCALARS: return SCALARS[type(t)]
    if isinstance(t, S.TRec): return '(rec ' + t.name + ''.join(' ' + ty(a) for a in t.args) + ')'
    if isinstance(t, S.TRef): return '(ref ' + ty(t.resource) + ')'
    if isinstance(t, S.TFn):
        caps = '-' if t.capabilities is None else names(t.capabilities)
        return '(fn ' + types(t.params) + ' ' + ty(t.ret) + ' ' + caps + ')'
    if isinstance(t, S.TArr): return '(arr ' + ty(t.elem) + ' ' + (t.size if isinstance(t.size, str) else expr(t.size)) + ')'
    raise TypeError(type(t).__name__)


def head(word, e): return '(' + word + pos(e)


def expr(e):
    if isinstance(e, S.Num): return head('num', e) + f' {e.value})'
    if isinstance(e, S.Flt): return head('flt', e) + ' ' + struct.pack('>d', e.value).hex() + ')'
    if isinstance(e, S.BoolLit): return head('bool', e) + (' true)' if e.value else ' false)')
    if isinstance(e, S.Str): return head('str', e) + ' x' + e.value.hex() + ')'
    if isinstance(e, S.Byte): return head('byte', e) + f' {e.value})'
    if isinstance(e, S.Var): return head('var', e) + ' ' + e.name + ')'
    if isinstance(e, S.Bin): return head('bin', e) + f' {e.op} {expr(e.left)} {expr(e.right)})'
    if isinstance(e, S.Un): return head('un', e) + f' {e.op} {expr(e.expr)})'
    if isinstance(e, S.Index): return head('index', e) + f' {expr(e.arr)} {expr(e.idx)})'
    if isinstance(e, S.Call): return head('call', e) + f' {e.name} {types(e.type_args)} {exprs(e.args)})'
    if isinstance(e, (S.Let, S.Using)):
        return head('let' if isinstance(e, S.Let) else 'using', e) + f' {e.name} {expr(e.value)} {expr(e.body)})'
    if isinstance(e, S.If): return head('if', e) + f' {expr(e.cond)} {expr(e.then)} {expr(e.els)})'
    if isinstance(e, (S.Sum, S.ArrC)):
        return head('sum' if isinstance(e, S.Sum) else 'arrc', e) + f' {e.var} {expr(e.lo)} {expr(e.hi)} {expr(e.body)})'
    if isinstance(e, S.Loop):
        def annot(a): return '-' if a is None else '(ann ' + ty(a[0]) + ' ' + exprs(a[1]) + ')'
        states = '(' + ' '.join(f'({n} {annot(a)} {expr(i)})' for n, a, i in zip(e.names, e.annots, e.inits)) + ')'
        return head('loop', e) + f' {states} {expr(e.cond)} {exprs(e.nexts)} {expr(e.yld)})'
    if isinstance(e, S.Check): return head('check', e) + f' {expr(e.pred)} {expr(e.body)})'
    if isinstance(e, S.Len): return head('len', e) + f' {expr(e.expr)})'
    if isinstance(e, S.Cast): return head('cast', e) + f' {ty(e.to)} {expr(e.expr)})'
    if isinstance(e, S.RecLit):
        return head('reclit', e) + f' {e.tname} {types(getattr(e, "type_args", ()))} {inits(e.fields)})'
    if isinstance(e, S.Field): return head('field', e) + f' {expr(e.expr)} {e.name})'
    if isinstance(e, S.With): return head('with', e) + f' {expr(e.expr)} {inits(e.fields)})'
    if isinstance(e, S.Match):
        arms = '(' + ' '.join(f'({v} {names(b)} {expr(body)})' for v, b, body in e.arms) + ')'
        return head('match', e) + f' {expr(e.expr)} {arms})'
    if isinstance(e, S.Try): return head('try', e) + f' {expr(e.expr)})'
    raise TypeError(type(e).__name__)


def bits(*flags): return ''.join('1' if f else '0' for f in flags)


def type_decl(d):
    variants = '-' if d.variants is None else '(' + ' '.join(f'({n} {types(p)})' for n, p in d.variants) + ')'
    fields = '(' + ' '.join(f'({n} {ty(t)})' for n, t in d.fields) + ')'
    return (f'(type {d.name} {d.pos[0]}:{d.pos[1]} {bits(d.sealed)} {bits(d.visible)} {names(d.type_params)} '
            f'{fields} {variants} {d.resource_drop or "-"})')


def fn_decl(f):
    caps = '-' if f.capabilities is None else names(f.capabilities)
    params = '(' + ' '.join(f'(param {p.name} {p.pos[0]}:{p.pos[1]} {bits(p.owned)} {bits(p.borrowed)} {ty(p.ty)} {exprs(p.preds)})'
                            for p in f.params) + ')'
    flags = bits(f.effect, f.external, f.exported, f.variadic, f.cold, f.inline, f.visible)
    return (f'(fn {f.name} {f.pos[0]}:{f.pos[1]} {flags} {caps} {names(f.type_params)} {params} {ty(f.ret)} '
            f'{exprs(f.ret_preds)} {expr(f.body)})')


def dump(text):
    try: program = S.parse(text)
    except S.SyntaxError_ as exc: return f'(error {exc.pos[0]}:{exc.pos[1]} {exc.msg})\n'
    lines = [f'(import x{path.encode().hex()} {p[0]}:{p[1]} {alias or "-"})' for path, p, alias in program.imports]
    lines += [type_decl(d) for d in program.types] + [fn_decl(f) for f in program.fns]
    return ''.join(line + '\n' for line in lines)


if __name__ == '__main__':
    try: text = Path(sys.argv[1]).read_text(encoding='utf-8')
    except (OSError, UnicodeError): sys.stdout.write('(ioerror)\n'); raise SystemExit(1)
    sys.stdout.buffer.write(dump(text).encode('utf-8'))
