"""Cross-iteration vectorization of sums and scalar array comprehensions.

A `sum(i in lo..hi) body` whose body is scalar arithmetic, possibly with a
data-dependent `loop` (Mandelbrot's escape iteration) and calls to small
scalar functions, is evaluated K iterations at a time: every scalar becomes a
<K x T> vector, `if` becomes `select`, and a `loop` runs while any lane is
still active, freezing finished lanes with masks. LLVM cannot do this itself
because each iteration's trip count is data dependent; the Neo graph has no
false dependencies between iterations, so the compiler may.

Sum eligibility is conservative: no arrays, records, checks, nested
comprehensions, integer division by a non-constant, or recursion. Array
comprehensions additionally permit captured scalar arrays with affine reads;
they use full vectors inside the common valid interval and scalar edges.
Neither path can allocate while evaluating a body, which also certifies it
for the Linux shared-address worker dispatcher.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from . import syntax as S

K = 16
ARRAY_LANES = 4

def sum_lanes(triple):
    """Lanes for masked `sum` loops. Darwin's ARM64 code keeps 16 f64 lanes
    fast; on Linux ARM64 (AAPCS64) the same IR spills and runs ~3x slower than
    8 lanes, measured with clang 18 and 20 on the same M1 Pro."""
    return 16 if 'apple' in triple else 8

def work_cost(e):
    """Conservative scheduling estimate; calls/loops keep default granularity.

    This is a work estimate, never a semantic/proof fact. Small straight-line
    vector loops often finish before a new kernel worker can be started.
    """
    if isinstance(e,(S.Call,S.Loop)): return None
    children=[work_cost(child) for child in S.children(e)]
    if any(cost is None for cost in children): return None
    weight=2 if isinstance(e,S.Index) else 8 if isinstance(e,S.Bin) and e.op in ('/','%') else 1
    return min(1000000,weight+sum(children))

def _scalar(t) -> bool:
    return t in (S.I64, S.F64, S.BOOL)

def affine_offset(e, name):
    if isinstance(e, S.Var) and e.name == name: return 0
    if isinstance(e, S.Bin) and isinstance(e.left, S.Var) and e.left.name == name and isinstance(e.right, S.Num):
        if e.op == '+': return e.right.value
        if e.op == '-': return -e.right.value
    return None

def eligible(body: S.Node, fns: Dict[str, S.Fn], depth: int = 0, array_var=None, reads=None, allow_libraries=False) -> bool:
    if depth > 4: return False
    def ok(e: S.Node) -> bool:
        if not _scalar(e.ty): return False
        if isinstance(e, (S.Num, S.Flt, S.BoolLit, S.Var)): return True
        if isinstance(e, S.Index) and array_var is not None:
            offset = affine_offset(e.idx, array_var)
            if not isinstance(e.arr, S.Var) or e.arr.name == array_var or e.ty not in (S.I64, S.F64) or offset is None or abs(offset) > 1048576: return False
            reads.append((e.arr.name, offset))
            return True
        if isinstance(e, S.Bin):
            if e.op in ("/", "%") and e.ty == S.I64 and not (isinstance(e.right, S.Num) and e.right.value != 0): return False
            return ok(e.left) and ok(e.right)
        if isinstance(e, S.Un): return ok(e.expr)
        if isinstance(e, S.Cast): return e.to in (S.I64, S.F64) and e.expr.ty in (S.I64, S.F64) and ok(e.expr)
        if isinstance(e, S.Let): return e.name != array_var and ok(e.value) and ok(e.body)
        if isinstance(e, S.If): return ok(e.cond) and ok(e.then) and ok(e.els)
        if isinstance(e, S.Loop):
            return array_var is None and all(_scalar(t) for t in e.state_tys) and all(ok(x) for x in e.inits) and ok(e.cond) \
                and all(ok(x) for x in e.nexts) and ok(e.yld)
        if isinstance(e, S.Call):
            if getattr(e, "builtin", None) == "sqrt": return ok(e.args[0])
            if getattr(e, "builtin", None): return False
            f = fns.get(e.name)
            if f is None or f.external or f.effect or getattr(f,'precompiled',False) or getattr(f,'native_library',False) and not allow_libraries or not _scalar(f.ret) or any(not _scalar(p.ty) for p in f.params): return False
            return all(ok(a) for a in e.args) and eligible(f.body, fns, depth + 1,allow_libraries=allow_libraries)
        return False
    return ok(body)

class VecGen:
    """Emits <K x T> code for a body; `lanes` is the <K x i64> vector of comprehension indices."""
    def __init__(self, gen, fb, fns: Dict[str, S.Fn], lanes=None):
        self.gen = gen; self.fb = fb; self.fns = fns
        self.lanes = K if lanes is None else lanes
        self.mask = None
        self.assumed = {}    # id(comparison) -> its value on every lane (interior_assumptions)

    def checked(self, operation, a, b, node):
        K = self.lanes
        bounds = self.gen.value_ranges
        left, right = bounds.get(id(getattr(node, 'left', None)), S_TOP), bounds.get(id(getattr(node, 'right', None)), S_TOP)
        safe = False
        if isinstance(node, S.Bin) and operation in ('add','sub','mul'):
            from . import ranges as R
            if left and right:
                if operation == 'add': lo,hi=left[0]+right[0],left[1]+right[1]
                elif operation == 'sub': lo,hi=left[0]-right[1],left[1]-right[0]
                else:
                    products=[x*y for x in left for y in right];lo,hi=min(products),max(products)
                safe=R.MIN<=lo<=hi<=R.MAX
        if not self.gen.checked_integer() or getattr(node,'arithmetic_proven',False) or safe:return self.fb.ins(f'{operation} <{K} x i64> {a}, {b}',f'<{K} x i64>').name
        if self.mask:
            a=self.fb.ins(f'select <{K} x i1> {self.mask}, <{K} x i64> {a}, <{K} x i64> zeroinitializer',f'<{K} x i64>').name
            b=self.fb.ins(f'select <{K} x i1> {self.mask}, <{K} x i64> {b}, <{K} x i64> zeroinitializer',f'<{K} x i64>').name
        ty=f'{{ <{K} x i64>, <{K} x i1> }}'
        result=self.fb.ins(f'call {ty} @llvm.s{operation}.with.overflow.v{K}i64(<{K} x i64> {a}, <{K} x i64> {b})',ty)
        value=self.fb.ins(f'extractvalue {result}, 0',f'<{K} x i64>')
        bad=self.fb.ins(f'extractvalue {result}, 1',f'<{K} x i1>')
        self.check_mask(bad.name,node)
        return value.name

    def check_mask(self, bad, node):
        K = self.lanes
        if self.mask:bad=self.fb.ins(f'and <{K} x i1> {bad}, {self.mask}',f'<{K} x i1>').name
        any_bad=self.fb.ins(f'call i1 @llvm.vector.reduce.or.v{K}i1(<{K} x i1> {bad})','i1')
        self.gen.trap_if(any_bad,node,'integer vector overflow')

    def vty(self, t) -> str:
        K = self.lanes
        return {S.I64: f"<{K} x i64>", S.F64: f"<{K} x double>", S.BOOL: f"<{K} x i1>"}[t]

    def splat(self, scalar: str, ty: str, t) -> str:
        K = self.lanes
        fb = self.fb
        a = fb.ins(f"insertelement {self.vty(t)} poison, {ty} {scalar}, i64 0", self.vty(t))
        return fb.ins(f"shufflevector {a}, {self.vty(t)} poison, <{K} x i32> zeroinitializer", self.vty(t)).name

    def const(self, val: str, t) -> str:
        K = self.lanes
        ty = {S.I64: "i64", S.F64: "double", S.BOOL: "i1"}[t]
        return "<" + ", ".join(f"{ty} {val}" for _ in range(K)) + ">"

    def gen_vec(self, e: S.Node, venv: Dict[str, str], senv) -> str:
        """venv: name -> vector SSA name; senv: scalar env (Slots) for captured outer variables."""
        K = self.lanes
        fb = self.fb
        vt = self.vty(e.ty)
        if isinstance(e, S.Num): return self.const(str(e.value), S.I64)
        if isinstance(e, S.Flt):
            from .llvm import fconst
            return self.const(fconst(e.value), S.F64)
        if isinstance(e, S.BoolLit): return self.const("true" if e.value else "false", S.BOOL)
        if isinstance(e, S.Var):
            if e.name in venv: return venv[e.name]
            s = senv[e.name]
            v = fb.load(s.ty, s.ptr)
            return self.splat(v.name, s.ty, e.ty)
        if isinstance(e, S.Index):
            # vector_array_loop has proved every speculative load in this full
            # vector lies inside its source array, including untaken branches.
            name, base = self.array_index
            offset = affine_offset(e.idx, name)
            slot = senv[e.arr.name]
            arr = fb.load(slot.ty, slot.ptr)
            data = fb.ins(f'extractvalue {arr}, 0', 'ptr')
            index = fb.ins(f'add i64 {base}, {offset}', 'i64')
            scalar = 'i64' if e.ty == S.I64 else 'double'
            ptr = fb.ins(f'getelementptr inbounds {scalar}, ptr {data.name}, i64 {index.name}', 'ptr')
            return fb.ins(f'load {vt}, ptr {ptr.name}, align 8',vt).name
        if isinstance(e, S.Bin):
            a = self.gen_vec(e.left, venv, senv)
            lt = e.left.ty; lvt = self.vty(lt)
            if e.op in ("&&", "||"):
                previous=self.mask
                rhs_mask=a if e.op=='&&' else fb.ins(f'xor {lvt} {a}, {self.const("true",S.BOOL)}',lvt).name
                self.mask=rhs_mask if previous is None else fb.ins(f'and {lvt} {previous}, {rhs_mask}',lvt).name
                b=self.gen_vec(e.right,venv,senv);self.mask=previous
                return fb.ins(f'select {lvt} {a}, {lvt} {b if e.op=="&&" else self.const("true",S.BOOL)}, {lvt} {self.const("false",S.BOOL) if e.op=="&&" else b}',vt).name
            b = self.gen_vec(e.right, venv, senv)
            fl = lt == S.F64
            if e.op in ("+", "-", "*", "/", "%"):
                op = {"+": "fadd" if fl else "add", "-": "fsub" if fl else "sub", "*": "fmul" if fl else "mul",
                      "/": "fdiv" if fl else "sdiv", "%": "srem"}[e.op]
                if not fl and e.op in ('+','-','*'):return self.checked(op,a,b,e)
                if e.op == '%' and not fl:
                    from .llvm import Val
                    reduced = self.gen.bounded_remainder(e, Val(a,lvt), Val(b,lvt), lanes=K)
                    if reduced is not None: return reduced.name
                if not fl and self.gen.checked_integer():
                    if self.mask:
                        a=fb.ins(f'select <{K} x i1> {self.mask}, {lvt} {a}, {lvt} zeroinitializer',lvt).name
                        b=fb.ins(f'select <{K} x i1> {self.mask}, {lvt} {b}, {lvt} {self.const("1",S.I64)}',lvt).name
                    minval=self.const('-9223372036854775808',S.I64);minus=self.const('-1',S.I64)
                    first=fb.ins(f'icmp eq {lvt} {a}, {minval}',f'<{K} x i1>')
                    second=fb.ins(f'icmp eq {lvt} {b}, {minus}',f'<{K} x i1>')
                    bad=fb.ins(f'and <{K} x i1> {first.name}, {second.name}',f'<{K} x i1>');self.check_mask(bad.name,e)
                return fb.ins(f"{op} {lvt} {a}, {b}", vt).name
            if fl:
                op = {"<": "olt", "<=": "ole", ">": "ogt", ">=": "oge", "==": "oeq", "!=": "une"}[e.op]
                return fb.ins(f"fcmp {op} {lvt} {a}, {b}", vt).name
            op = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "eq", "!=": "ne"}[e.op]
            return fb.ins(f"icmp {op} {lvt} {a}, {b}", vt).name
        if isinstance(e, S.Un):
            if e.op=='-' and isinstance(e.expr,S.Num) and e.expr.value==1<<63:return self.const('-9223372036854775808',S.I64)
            a = self.gen_vec(e.expr, venv, senv)
            if e.op == "!": return fb.ins(f"xor {vt} {a}, {self.const('true', S.BOOL)}", vt).name
            if e.ty == S.F64: return fb.ins(f"fneg {vt} {a}", vt).name
            return self.checked('sub','zeroinitializer',a,e)
        if isinstance(e, S.Cast):
            a = self.gen_vec(e.expr, venv, senv)
            if e.to == S.F64: return fb.ins(f"sitofp <{K} x i64> {a} to <{K} x double>", vt).name
            if self.mask:a=fb.ins(f'select <{K} x i1> {self.mask}, <{K} x double> {a}, <{K} x double> zeroinitializer',f'<{K} x double>').name
            from .llvm import fconst
            low=fb.ins(f'fcmp oge <{K} x double> {a}, {self.const(fconst(float(-(1<<63))),S.F64)}',f'<{K} x i1>')
            high=fb.ins(f'fcmp olt <{K} x double> {a}, {self.const(fconst(float(1<<63)),S.F64)}',f'<{K} x i1>')
            good=fb.ins(f'and <{K} x i1> {low.name}, {high.name}',f'<{K} x i1>')
            bad=fb.ins(f'xor <{K} x i1> {good.name}, {self.const("true",S.BOOL)}',f'<{K} x i1>');self.check_mask(bad.name,e)
            return fb.ins(f"fptosi <{K} x double> {a} to <{K} x i64>", vt).name
        if isinstance(e, S.Let):
            v = self.gen_vec(e.value, venv, senv)
            v2 = dict(venv); v2[e.name] = v
            return self.gen_vec(e.body, v2, senv)
        if isinstance(e, S.If):
            fixed = static_condition(e.cond, self.assumed) if self.assumed else None
            if fixed is not None: return self.gen_vec(e.then if fixed else e.els, venv, senv)
            c = self.gen_vec(e.cond, venv, senv)
            previous=self.mask
            self.mask=c if previous is None else fb.ins(f'and <{K} x i1> {previous}, {c}',f'<{K} x i1>').name
            a = self.gen_vec(e.then, venv, senv)
            inverse=fb.ins(f'xor <{K} x i1> {c}, {self.const("true",S.BOOL)}',f'<{K} x i1>').name
            self.mask=inverse if previous is None else fb.ins(f'and <{K} x i1> {previous}, {inverse}',f'<{K} x i1>').name
            b = self.gen_vec(e.els, venv, senv)
            self.mask=previous
            return fb.ins(f"select <{K} x i1> {c}, {vt} {a}, {vt} {b}", vt).name
        if isinstance(e, S.Call):
            if getattr(e, "builtin", None) == "sqrt":
                a = self.gen_vec(e.args[0], venv, senv)
                return fb.ins(f"call <{K} x double> @llvm.sqrt.v{K}f64(<{K} x double> {a})", vt).name
            f = self.fns[e.name]
            v2 = dict(venv)
            for p, a in zip(f.params, e.args):
                v2[p.name] = self.gen_vec(a, venv, senv)         # inline: parameters become lane vectors
            return self.gen_vec(f.body, v2, senv)
        if isinstance(e, S.Loop):
            return self.gen_loop(e, venv, senv)
        raise TypeError(type(e))

    def gen_loop(self, e: S.Loop, venv, senv) -> str:
        """Masked loop: run while any lane's condition holds; finished lanes keep their state."""
        K = self.lanes
        fb = self.fb
        tys = [self.vty(t) for t in e.state_tys]
        ptrs = []
        for x, ty in zip(e.inits, tys):
            p = fb.alloca(ty); fb.store(_V(self.gen_vec(x, venv, senv), ty), p); ptrs.append(p)
        parent_mask=self.mask
        mask_p = fb.alloca(f"<{K} x i1>"); fb.store(_V(parent_mask or self.const("true", S.BOOL), f"<{K} x i1>"), mask_p)
        head, body, exit_ = fb.label("vloop_head"), fb.label("vloop_body"), fb.label("vloop_exit")
        fb.br(head); fb.block(head)
        v2 = dict(venv)
        for n, p, ty in zip(e.names, ptrs, tys): v2[n] = fb.load(ty, p).name
        m = fb.load(f"<{K} x i1>", mask_p)
        self.mask=m.name
        c = self.gen_vec(e.cond, v2, senv)
        m2 = fb.ins(f"and <{K} x i1> {m.name}, {c}", f"<{K} x i1>")
        fb.store(m2, mask_p)
        any_ = fb.ins(f"call i1 @llvm.vector.reduce.or.v{K}i1(<{K} x i1> {m2.name})", "i1")
        fb.cbr(any_, body, exit_); fb.block(body)
        self.mask=m2.name
        nexts = [self.gen_vec(x, v2, senv) for x in e.nexts]
        for n, p, ty, nx in zip(e.names, ptrs, tys, nexts):
            sel = fb.ins(f"select <{K} x i1> {m2.name}, {ty} {nx}, {ty} {v2[n]}", ty)
            fb.store(sel, p)
        fb.br(head); fb.block(exit_)
        v3 = dict(venv)
        for n, p, ty in zip(e.names, ptrs, tys): v3[n] = fb.load(ty, p).name
        self.mask=parent_mask
        return self.gen_vec(e.yld, v3, senv)

class _V:
    """Minimal stand-in for llvm.Val (name, ty) to reuse FuncBuilder.store."""
    def __init__(self, name, ty): self.name = name; self.ty = ty
    def __str__(self): return f"{self.ty} {self.name}"

S_TOP = (-(1 << 63), (1 << 63)-1)

def static_condition(c, assumed):
    """The value of a boolean condition when the comparisons in `assumed`
    have the recorded values, or None when it still depends on the lane."""
    if id(c) in assumed: return assumed[id(c)]
    if isinstance(c, S.BoolLit): return c.value
    if isinstance(c, S.Un) and c.op == '!':
        inner = static_condition(c.expr, assumed)
        return None if inner is None else not inner
    if isinstance(c, S.Bin) and c.op in ('&&', '||'):
        a, b = static_condition(c.left, assumed), static_condition(c.right, assumed)
        if c.op == '||': return True if True in (a, b) else False if a is False and b is False else None
        return False if False in (a, b) else True if a is True and b is True else None
    return None

FLIP = {'<': '>', '<=': '>=', '>': '<', '>=': '<=', '==': '==', '!=': '!='}

def index_atom(c, var, bound, env):
    """`i + c1 OP x` with x a constant or a captured i64 scalar plus a
    constant, as (OP with the index on the left, scalar name or None,
    constant k): the comparison is `i OP name + k`. Names rebound by an
    enclosing `let` (bound) do not count."""
    if not (isinstance(c, S.Bin) and c.op in FLIP and c.left.ty == S.I64): return None
    def offset(x):
        if isinstance(x, S.Var) and x.name == var and x.name not in bound: return 0
        if isinstance(x, S.Bin) and x.op in ('+', '-') and isinstance(x.right, S.Num):
            inner = offset(x.left)
            return None if inner is None else inner + (x.right.value if x.op == '+' else -x.right.value)
        if isinstance(x, S.Bin) and x.op == '+' and isinstance(x.left, S.Num):
            inner = offset(x.right)
            return None if inner is None else inner + x.left.value
        return None
    def invariant(x):
        if isinstance(x, S.Num): return (None, x.value)
        if isinstance(x, S.Var) and x.name != var and x.name not in bound and x.name in env \
                and env[x.name].ty == 'i64' and x.ty == S.I64: return (x.name, 0)
        if isinstance(x, S.Bin) and x.op in ('+', '-') and isinstance(x.right, S.Num):
            inner = invariant(x.left)
            return None if inner is None else (inner[0], inner[1] + (x.right.value if x.op == '+' else -x.right.value))
        return None
    for a, b, op in ((c.left, c.right, c.op), (c.right, c.left, FLIP[c.op])):
        k, other = offset(a), invariant(b)
        if k is not None and other is not None and abs(other[1] - k) < 1 << 62: return (op, other[0], other[1] - k)
    return None

def index_atoms(x, var, env, bound=frozenset(), ifs=None):
    """Every index comparison (index_atom) in a comprehension body, as
    (comparison, op, name, k). Call bodies are not followed; `ifs` collects
    each `if` with the names rebound around it."""
    found = []
    def visit(x, bound):
        atom = index_atom(x, var, bound, env)
        if atom: found.append((x,) + atom)
        if isinstance(x, S.If) and ifs is not None: ifs.append((x, bound))
        if isinstance(x, (S.If, S.Bin, S.Un, S.Cast)):
            for child in S.children(x): visit(child, bound)
        elif isinstance(x, S.Let):
            visit(x.value, bound); visit(x.body, bound | {x.name})
    visit(x, bound)
    return found

def invariant_value(fb, env, name, k):
    """name + k as (i64 value, i1 overflowed), or the constant k."""
    if name is None: return fb.ins(f'add i64 0, {k}', 'i64'), None
    value = fb.load('i64', env[name].ptr)
    summed = fb.ins(f'call {{ i64, i1 }} @llvm.sadd.with.overflow.i64(i64 {value.name}, i64 {k})', '{ i64, i1 }')
    return fb.ins(f'extractvalue {summed}, 0', 'i64'), fb.ins(f'extractvalue {summed}, 1', 'i1')

def interior_assumptions(gen, fb, e, env, lower, upper):
    """Boundary tests such as `i == 0 || i + 1 == n` are false on every lane
    of the vector interior whenever each tested index lies outside
    [lower, upper). Returns ({id(comparison): value}, guard): the loop
    specialized for those values may run when `guard` holds at run time.
    Only `==` / `!=` index comparisons count, and only in `if` conditions
    they decide; the guard compares the actual values, so nothing depends on
    what the checker knew about them."""
    ifs = []
    index_atoms(e.body, e.var, env, ifs=ifs)
    atoms = {}
    for node, bound in ifs:
        tests = [a for a in index_atoms(node.cond, e.var, env, bound) if a[1] in ('==', '!=')]
        if tests and static_condition(node.cond, {id(a[0]): a[1] == '!=' for a in tests}) is not None:
            for a in tests: atoms[id(a[0])] = a
    if not atoms: return {}, None
    guard = None
    for c, op, name, k in atoms.values():
        target, wrapped = invariant_value(fb, env, name, k)
        below = fb.ins(f'icmp slt i64 {target.name}, {lower.name}', 'i1')
        above = fb.ins(f'icmp sge i64 {target.name}, {upper.name}', 'i1')
        outside = fb.ins(f'or i1 {below.name}, {above.name}', 'i1')
        if wrapped is not None: outside = fb.ins(f'and i1 {outside.name}, ' + fb.ins(f'xor i1 {wrapped.name}, true', 'i1').name, 'i1')
        guard = outside if guard is None else fb.ins(f'and i1 {guard.name}, {outside.name}', 'i1')
    return {id(c): op == '!=' for c, op, _, _ in atoms.values()}, guard

def split_counted_loop(gen, fb, e, lo, hi, env, body_fn):
    """A scalar comprehension loop whose body compares its index with one
    loop-invariant bound (`k >= 2`, `if i < m then … else …`) runs as two
    loops split at that bound, each compiled with the comparisons fixed, so a
    body like `k >= 2` becomes two constant fills. Comparisons against
    different bounds, or none, keep the single loop."""
    atoms = [a for a in index_atoms(e.body, e.var, env) if a[1] not in ('==', '!=')]
    # i < t and i <= t-1 split at t; i >= t and i > t-1 are true from t on.
    splits = {(name, k + (1 if op in ('<=', '>') else 0)) for _, op, name, k in atoms}
    if len(splits) != 1: return gen.counted_loop(lo, hi, e.var, env, body_fn)
    (name, k), = splits
    at, wrapped = invariant_value(fb, env, name, k)
    if wrapped is not None:
        # name + k beyond i64 lies above (k > 0) or below (k < 0) every index.
        at = fb.ins(f'select i1 {wrapped.name}, i64 {(1 << 63) - 1 if k > 0 else -(1 << 63)}, i64 {at.name}', 'i64')
    at = fb.ins(f'select i1 ' + fb.ins(f'icmp slt i64 {at.name}, {lo.name}', 'i1').name + f', i64 {lo.name}, i64 {at.name}', 'i64')
    at = fb.ins(f'select i1 ' + fb.ins(f'icmp sgt i64 {at.name}, {hi.name}', 'i1').name + f', i64 {hi.name}, i64 {at.name}', 'i64')
    saved = gen.assumed
    for first, last, below in ((lo, at, True), (at, hi, False)):
        gen.assumed = {**saved, **{id(c): (op in ('<', '<=')) == below for c, op, _, _ in atoms}}
        gen.counted_loop(first, last, e.var, env, body_fn)
    gen.assumed = saved

def vector_array_loop(gen, fb, e, lo, hi, env, out, origin, reads):
    """Full contiguous vectors in the common safe interior; scalar edges/tail.

    Intersect the valid intervals of *all* loads, even under branches. This
    avoids speculative out-of-bounds loads without masked gathers or padding.
    """
    K = ARRAY_LANES
    lower, upper = lo, hi
    for name, offset in sorted(set(reads)):
        arr = fb.load(env[name].ty, env[name].ptr)
        length = fb.ins(f'extractvalue {arr}, 1','i64')
        if offset < 0:
            lower = fb.ins(f'select i1 '+fb.ins(f'icmp slt i64 {lower.name}, {-offset}','i1').name+f', i64 {-offset}, i64 {lower.name}','i64')
            # Saturate len-offset, so even a large borrowed array cannot wrap.
            limit = (1 << 63)-1+offset
            too_large = fb.ins(f'icmp sgt i64 {length.name}, {limit}','i1')
            end = fb.ins(f'sub i64 {length.name}, {offset}','i64')
            end = fb.ins(f'select {too_large}, i64 {(1<<63)-1}, {end}','i64')
        else:
            end = fb.ins(f'sub i64 {length.name}, {offset}','i64')
        upper = fb.ins(f'select i1 '+fb.ins(f'icmp slt i64 {end.name}, {upper.name}','i1').name+f', {end}, {upper}','i64')
    # Clamp an empty interior to a point in the original iteration interval.
    lower = fb.ins(f'select i1 '+fb.ins(f'icmp sgt i64 {lower.name}, {hi.name}','i1').name+f', {hi}, {lower}','i64')
    upper = fb.ins(f'select i1 '+fb.ins(f'icmp slt i64 {upper.name}, {lower.name}','i1').name+f', {lower}, {upper}','i64')
    def scalar(inner, i):
        value, _ = gen.gen(e.body, inner, par=False)
        index = fb.ins(f'sub i64 {i.name}, {origin.name}','i64')
        gen.store_elem(out,index,e.ty,value)
    gen.counted_loop(lo,lower,e.var,env,scalar)
    ip=fb.alloca('i64');fb.store(lower,ip)
    def vector_loop(assumed):
        head,body,end=fb.label('varr_cond'),fb.label('varr_body'),fb.label('varr_end')
        fb.br(head);fb.block(head)
        i=fb.load('i64',ip)
        remaining=fb.ins(f'sub i64 {upper.name}, {i.name}','i64')
        fb.cbr(fb.ins(f'icmp sge i64 {remaining.name}, {K}','i1'),body,end);fb.block(body)
        vg=VecGen(gen,fb,gen.fn_map,lanes=K);vg.array_index=(e.var,i.name);vg.assumed=assumed
        base=vg.splat(i.name,'i64',S.I64)
        lanes=fb.ins(f'add <{K} x i64> {base}, <'+', '.join(f'i64 {k}' for k in range(K))+'>',f'<{K} x i64>')
        value=vg.gen_vec(e.body,{e.var:lanes.name},env)
        data=fb.ins(f'extractvalue {out}, 0','ptr')
        index=fb.ins(f'sub i64 {i.name}, {origin.name}','i64')
        scalar_ty='i64' if e.ty.elem==S.I64 else 'double'
        ptr=fb.ins(f'getelementptr inbounds {scalar_ty}, ptr {data.name}, i64 {index.name}','ptr')
        fb.emit(f'store {vg.vty(e.ty.elem)} {value}, ptr {ptr.name}, align 8')
        fb.store(fb.ins(f'add i64 {i.name}, {K}','i64'),ip);fb.br(head);fb.block(end)
    # Edge tests that no interior lane can satisfy get a loop without them;
    # the general masked loop remains for any other run-time values.
    assumed,guard=interior_assumptions(gen,fb,e,env,lower,upper)
    if assumed:
        special,general,joined=fb.label('varr_interior'),fb.label('varr_general'),fb.label('varr_joined')
        fb.cbr(guard,special,general)
        fb.block(special);vector_loop(assumed);fb.br(joined)
        fb.block(general);vector_loop({});fb.br(joined)
        fb.block(joined)
    else: vector_loop({})
    gen.counted_loop(fb.load('i64',ip),hi,e.var,env,scalar)

def vector_sum_loop(gen, fb, e: S.Sum, lo, hi, env, acc_ptr: str, fns: Dict[str, S.Fn]):
    """Accumulate sum(body) over [lo, hi) into *acc_ptr, K lanes at a time."""
    vg = VecGen(gen, fb, fns)
    t = e.ty; vt = vg.vty(t)
    vacc = fb.alloca(vt); fb.store(_V("zeroinitializer", vt), vacc)
    ip = fb.alloca("i64"); fb.store(_V(lo.name, "i64"), ip)
    cond, body, end = fb.label("vsum_cond"), fb.label("vsum_body"), fb.label("vsum_end")
    fb.br(cond); fb.block(cond)
    i = fb.load("i64", ip)
    c = fb.ins(f"icmp slt i64 {i.name}, {hi.name}", "i1")
    fb.cbr(c, body, end); fb.block(body)
    base = vg.splat(i.name, "i64", S.I64)
    lanes = fb.ins(f"add <{K} x i64> {base}, <{', '.join(f'i64 {k}' for k in range(K))}>", f"<{K} x i64>")
    hiv = vg.splat(hi.name, "i64", S.I64)
    remaining=fb.ins(f'sub i64 {hi.name}, {i.name}','i64')
    remainv=vg.splat(remaining.name,'i64',S.I64)
    offsets='<'+', '.join(f'i64 {k}' for k in range(K))+'>'
    active = fb.ins(f"icmp slt <{K} x i64> {offsets}, {remainv}", f"<{K} x i1>")
    last = fb.ins(f"sub i64 {hi.name}, 1", "i64")
    lastv = vg.splat(last.name, "i64", S.I64)
    idx = fb.ins(f"select <{K} x i1> {active.name}, <{K} x i64> {lanes.name}, <{K} x i64> {lastv}", f"<{K} x i64>")
    venv = {e.var: idx.name}                      # inactive lanes recompute the last valid index and are masked out
    vg.mask=active.name
    val = vg.gen_vec(e.body, venv, env)
    masked = fb.ins(f"select <{K} x i1> {active.name}, {vt} {val}, {vt} zeroinitializer", vt)
    old = fb.load(vt, vacc)
    op = "fadd reassoc" if t == S.F64 else "add"
    summed=vg.checked('add',old.name,masked.name,e) if t==S.I64 else fb.ins(f"{op} {vt} {old.name}, {masked.name}",vt).name
    if t==S.I64:summed=fb.ins(f'select <{K} x i1> {active.name}, {vt} {summed}, {vt} {old.name}',vt).name
    fb.store(_V(summed,vt),vacc)
    advance=fb.ins(f'add i64 {i.name}, {K}','i64')
    near=fb.ins(f'icmp slt i64 {remaining.name}, {K}','i1')
    i2=fb.ins(f'select i1 {near.name}, i64 {hi.name}, i64 {advance.name}','i64');fb.store(i2,ip)
    fb.br(cond); fb.block(end)
    v = fb.load(vt, vacc)
    if t == S.F64:
        red = fb.ins(f"call reassoc double @llvm.vector.reduce.fadd.v{K}f64(double 0.0, <{K} x double> {v.name})", "double")
        old = fb.load("double", acc_ptr); fb.store(fb.ins(f"fadd reassoc double {old.name}, {red.name}", "double"), acc_ptr)
    else:
        old=fb.load('i64',acc_ptr)
        for lane in range(K):
            value=fb.ins(f'extractelement {vt} {v.name}, i64 {lane}','i64')
            old=gen.checked_operation('+',old,value,e) if gen.checked_integer() else fb.ins(f'add {old}, {value.name}','i64')
        fb.store(old,acc_ptr)
