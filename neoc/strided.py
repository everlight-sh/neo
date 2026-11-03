"""Unrolled prefix for strided constant-store loops.

    loop (a = m, j = start) while j < x next (set(a, j, v), j + s) yield ...

with x, v and s loop-invariant stores v at start, start + s, ... The ordinary
loop does one store, an overflow-checked add and a compare per element. When
the array state is written in place (set_only_state), this prefix stores four
elements per iteration while j + 3s < min(x, len(a)); its guard checks the
actual length, step and start once, so no index or addition can leave range.
The ordinary loop then runs the remaining iterations with its usual checks.

On x86-64, when each store lands on its own 64-byte line (step * size >= 64)
of an array of at least 4 MiB, a bool, u8 or i64 element is loaded first and
stored only if it differs. The line is fetched either way; a skipped store
leaves it clean, so it is not written back to memory. A sieve's marking
passes mostly find composites already marked: the 100M-flag sieve went from
390 to 368 ms (429 to 415 ms without huge pages) on an EPYC-Milan, and a
never-redundant pass costs 2% more. f64 is excluded because equal floats can
differ in bits (0.0 and -0.0).
"""
from . import syntax as S

def _invariant(node, states):
    if isinstance(node, (S.Num, S.BoolLit, S.Byte)): return True
    return isinstance(node, S.Var) and node.name not in states

def match(e):
    """(array state k, index state k, bound, value, step) or None."""
    if len(e.names) != 2: return None
    states = set(e.names)
    for ka, kj in ((0, 1), (1, 0)):
        a, j = e.names[ka], e.names[kj]
        t = e.state_tys[ka]
        if not isinstance(t, S.TArr) or t.elem not in (S.I64, S.F64, S.BOOL, S.U8) or e.state_tys[kj] != S.I64: continue
        c, put, step = e.cond, e.nexts[ka], e.nexts[kj]
        if not (isinstance(c, S.Bin) and c.op == '<' and isinstance(c.left, S.Var) and c.left.name == j
                and _invariant(c.right, states) and c.right.ty == S.I64): continue
        if not (isinstance(put, S.Call) and getattr(put, 'builtin', None) == 'set' and len(put.args) == 3): continue
        target, index, value = put.args
        if not (isinstance(target, S.Var) and target.name == a and isinstance(index, S.Var) and index.name == j
                and _invariant(value, states)): continue
        if not (isinstance(step, S.Bin) and step.op == '+' and isinstance(step.left, S.Var) and step.left.name == j
                and _invariant(step.right, states)): continue
        return ka, kj, c.right, value, step.right
    return None

def prefix(gen, e, slots, env, par):
    found = match(e)
    if found is None: return
    ka, kj, bound, value, step = found
    array, index = slots[ka], slots[kj]
    if not getattr(array, 'always_unique', False): return
    fb, t = gen.fb, e.state_tys[ka]
    x = gen.gen(bound, env, par)[0]
    v = gen.gen(value, env, par)[0]
    s = gen.gen(step, env, par)[0]
    arr = fb.load(array.ty, array.ptr)
    length = fb.ins(f'extractvalue {arr}, 1', 'i64')
    end = fb.ins(f'select i1 ' + fb.ins(f'icmp slt i64 {x.name}, {length.name}', 'i1').name + f', i64 {x.name}, i64 {length.name}', 'i64')
    start = fb.load('i64', index.ptr)
    # 1 <= s <= 2^60, 0 <= start and end <= 2^62: j + 4s < end + s stays in i64.
    checks = [f'icmp sge i64 {s.name}, 1', f'icmp sle i64 {s.name}, {1 << 60}', f'icmp sge i64 {start.name}, 0', f'icmp sle i64 {end.name}, {1 << 62}']
    ok = None
    for check in checks:
        bit = fb.ins(check, 'i1')
        ok = bit if ok is None else fb.ins(f'and i1 {ok.name}, {bit.name}', 'i1')
    three = fb.ins(f'mul i64 {s.name}, 3', 'i64')
    limit = fb.ins(f'sub i64 {end.name}, {three.name}', 'i64')
    def unrolled(checked):
        head, body, done = fb.label('stride_cond'), fb.label('stride_body'), fb.label('stride_done')
        fb.br(head); fb.block(head)
        j = fb.load('i64', index.ptr)
        more = fb.ins(f'icmp slt i64 {j.name}, {limit.name}', 'i1')
        fb.cbr(fb.ins(f'and i1 {ok.name}, {more.name}', 'i1'), body, done); fb.block(body)
        at = j
        for k in range(4):
            if k: at = fb.ins(f'add nsw i64 {at.name}, {s.name}', 'i64')
            if checked:
                old = gen.load_elem(arr, at, t)
                put, skip = fb.label('stride_put'), fb.label('stride_next')
                fb.cbr(fb.ins(f'icmp ne {old}, {v.name}', 'i1'), put, skip); fb.block(put)
                gen.store_elem(arr, at, t, v); fb.br(skip); fb.block(skip)
            else: gen.store_elem(arr, at, t, v)
        fb.store(fb.ins(f'add nsw i64 {at.name}, {s.name}', 'i64'), index.ptr)
        fb.br(head); fb.block(done)
    if gen.triple.startswith('x86_64') and t.elem in (S.BOOL, S.U8, S.I64):
        size = 8 if t.elem == S.I64 else 1
        sparse = fb.ins(f'icmp sge i64 {s.name}, {64 // size}', 'i1')
        large = fb.ins(f'icmp sge i64 {length.name}, {(4 << 20) // size}', 'i1')
        checked, plain, joined = fb.label('stride_checked'), fb.label('stride_plain'), fb.label('stride_joined')
        fb.cbr(fb.ins(f'and i1 {sparse.name}, {large.name}', 'i1'), checked, plain)
        fb.block(checked); unrolled(True); fb.br(joined)
        fb.block(plain); unrolled(False); fb.br(joined)
        fb.block(joined)
    else: unrolled(False)
