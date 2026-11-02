"""Conservative whole-program integer/array-element intervals for pure code.

Intervals describe machine i64 values, not mathematical integers: an operation
that might wrap loses its bound. Calls from effects/FFI start with unknown
inputs. Loops and recursive calls use widening and converge before any result
is used by code generation. This pass never adds a proof assumption.
"""
from . import syntax as S

MIN, MAX = -(1 << 63), (1 << 63) - 1
TOP = (MIN, MAX)


def join(a, b):
    if a is None: return b
    if b is None: return a
    return min(a[0], b[0]), max(a[1], b[1])


def widen(old, new):
    if old is None or new is None: return join(old, new)
    return (MIN if new[0] < old[0] else old[0],
            MAX if new[1] > old[1] else old[1])


def bounded(lo, hi):
    return (lo, hi) if MIN <= lo <= hi <= MAX else TOP


def trunc(a, b):
    return (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)


def binary(op, a, b):
    if a is None or b is None: return None
    if op == '+': return bounded(a[0] + b[0], a[1] + b[1])
    if op == '-': return bounded(a[0] - b[1], a[1] - b[0])
    if op == '*':
        values = [x*y for x in a for y in b]
        return bounded(min(values), max(values))
    if op in ('%', '/') and b[0] == b[1] and b[0] > 0:
        d = b[0]
        if op == '/': return trunc(a[0], d), trunc(a[1], d)
        return (max(a[0], 1-d) if a[0] < 0 else 0,
                min(a[1], d-1) if a[1] > 0 else 0)
    return TOP


def refine(condition, env, truth):
    """Refine signed variable comparisons on a branch, without assuming overflow facts."""
    if isinstance(condition, S.Un) and condition.op == '!':
        return refine(condition.expr, env, not truth)
    if not isinstance(condition, S.Bin): return env
    op, left, right = condition.op, condition.left, condition.right
    if (op == '&&' and truth) or (op == '||' and not truth):
        return refine(right, refine(left, env, truth), truth)
    def constant(e):
        if isinstance(e, S.Num) and MIN <= e.value <= MAX: return e.value
        if isinstance(e, S.Un) and e.op == '-' and isinstance(e.expr, S.Num) and MIN <= -e.expr.value <= MAX:
            return -e.expr.value
        return None
    value = constant(right)
    if value is None and constant(left) is not None:
        left, right, value = right, left, constant(left)
        op = {'<': '>', '<=': '>=', '>': '<', '>=': '<=', '==': '==', '!=': '!='}.get(op, '')
    if value is None or not isinstance(left, S.Var) or left.ty != S.I64: return env
    if not truth: op = {'<': '>=', '<=': '>', '>': '<=', '>=': '<', '==': '!=', '!=': '=='}.get(op, '')
    a = env.get(left.name, TOP)
    if a is None: return env
    lo, hi = a
    if op == '<': hi = min(hi, value-1)
    elif op == '<=': hi = min(hi, value)
    elif op == '>': lo = max(lo, value+1)
    elif op == '>=': lo = max(lo, value)
    elif op == '==': lo, hi = max(lo, value), min(hi, value)
    else: return env
    inner = dict(env); inner[left.name] = (lo, hi) if lo <= hi else None
    return inner


class Analysis:
    def __init__(self, fns):
        self.all = {f.name: f for f in fns}
        self.fns = {f.name: f for f in fns if not f.external and not f.effect}
        self.inputs = {name: None for name in self.fns}
        self.outputs = {name: None for name in self.fns}
        self.nodes = {}
        self.round = 0

    def root(self, f):
        if f.name in self.inputs: self.inputs[f.name] = [TOP] * len(f.params)

    def run(self):
        for f in self.all.values():
            if f.exported or f.name == 'main': self.root(f)
            if f.external: continue
            def scan(e):
                if isinstance(e, S.Call):
                    if f.effect and e.name in self.fns: self.root(self.fns[e.name])
                    for attr in ('handler', 'target'):
                        callback = getattr(e, attr, None)
                        if callback is not None: self.root(callback)
                for child in S.children(e): scan(child)
            scan(f.body)
        for self.round in range(64):
            before = repr((self.inputs, self.outputs))
            self.nodes = {}
            for name, f in self.fns.items():
                args = self.inputs[name]
                if args is None: continue
                value = self.eval(f.body, dict(zip((p.name for p in f.params), args)))
                combine = widen if self.round >= 8 else join
                self.outputs[name] = combine(self.outputs[name], value)
            if before == repr((self.inputs, self.outputs)):
                return {node: value for node, value in self.nodes.items() if value is not None}
        return {}  # Refuse optimization if the abstract interpretation did not converge.

    def eval(self, e, env):
        result = self.expr(e, env)
        self.nodes[id(e)] = join(self.nodes.get(id(e)), result)
        return result

    def expr(self, e, env):
        ev = lambda x: self.eval(x, env)
        if isinstance(e, S.Num): return bounded(e.value, e.value)
        if isinstance(e, S.Byte): return e.value, e.value
        if isinstance(e, S.Var): return env.get(e.name, TOP)
        if isinstance(e, S.Len): ev(e.expr); return 0, MAX
        if isinstance(e, S.Bin):
            a, b = ev(e.left), ev(e.right)
            return binary(e.op, a, b) if e.ty == S.I64 else TOP
        if isinstance(e, S.Un):
            a = ev(e.expr)
            return bounded(-a[1], -a[0]) if a is not None and e.ty == S.I64 and e.op == '-' else TOP
        if isinstance(e, S.Cast):
            a = ev(e.expr)
            if a is None: return None
            if e.to == S.U8: return 0, 255
            if e.to == S.I32:
                return a if -(1 << 31) <= a[0] <= a[1] < (1 << 31) else (-(1 << 31), (1 << 31)-1)
            if e.to == S.I64 and e.expr.ty == S.U8: return 0, 255
            if e.to == S.I64 and e.expr.ty == S.I32: return a
            return TOP
        if isinstance(e, S.Index):
            a = ev(e.arr); ev(e.idx)
            return a if e.ty == S.I64 else TOP
        if isinstance(e, S.Let):
            value = ev(e.value); inner = dict(env); inner[e.name] = value
            return self.eval(e.body, inner)
        if isinstance(e, S.If):
            ev(e.cond)
            return join(self.eval(e.then, refine(e.cond, env, True)),
                        self.eval(e.els, refine(e.cond, env, False)))
        if isinstance(e, (S.ArrC, S.Sum)):
            lo, hi = ev(e.lo), ev(e.hi)
            inner = dict(env)
            inner[e.var] = (lo[0], max(lo[0], hi[1]-1)) if lo and hi else TOP
            value = self.eval(e.body, inner)
            return value if isinstance(e, S.ArrC) and e.ty.elem == S.I64 else TOP
        if isinstance(e, S.Loop):
            values = [ev(x) for x in e.inits]
            for iteration in range(16):
                inner = dict(env); inner.update(zip(e.names, values))
                self.eval(e.cond, inner)
                nexts = [self.eval(x, inner) for x in e.nexts]
                combine = widen if iteration >= 3 else join
                updated = [combine(a, b) for a, b in zip(values, nexts)]
                if updated == values: break
                values = updated
            else: values = [TOP] * len(values)
            inner = dict(env); inner.update(zip(e.names, values))
            self.eval(e.cond, inner)
            for x in e.nexts: self.eval(x, inner)
            return self.eval(e.yld, inner)
        if isinstance(e, S.Check): ev(e.pred); return ev(e.body)
        if isinstance(e, S.Call):
            builtin = getattr(e, 'builtin', None)
            if builtin in ('addr', 'serve'): return TOP
            args = [ev(a) for a in e.args]
            if builtin == 'set': return join(args[0], args[2])
            if builtin == 'concat':
                value = None
                for a in args: value = join(value, a)
                return value
            if e.name not in self.fns: return TOP
            if any(a is None for a in args): return None
            old = self.inputs[e.name]
            combine = widen if self.round >= 8 else join
            self.inputs[e.name] = args if old is None else [combine(a, b) for a, b in zip(old, args)]
            return self.outputs[e.name]
        for child in S.children(e): ev(child)
        return TOP


def analyze(fns):
    return Analysis(fns).run()
