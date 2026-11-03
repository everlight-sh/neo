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
WIDTH = 16
ARRAY_LANES = 4
ARRAY_WIDTH = 4

def sum_lanes(triple):
    """Lanes for masked `sum` loops. Darwin's ARM64 code keeps 16 f64 lanes
    fast; on Linux ARM64 (AAPCS64) the same IR spills and runs ~3x slower than
    8 lanes, measured with clang 18 and 20 on the same M1 Pro."""
    return 16 if 'apple' in triple else 8

def sum_width(triple):
    """Lanes per vector of a masked `sum` loop (see VecGen): one 128-bit NEON
    register of f64/i64 on Linux AArch64, the whole <K x T> vector elsewhere."""
    return 2 if triple.startswith(('aarch64', 'arm64')) and 'apple' not in triple else sum_lanes(triple)

def array_width(triple):
    """Lanes per vector of an array comprehension (see VecGen), as sum_width."""
    return 2 if triple.startswith(('aarch64', 'arm64')) and 'apple' not in triple else ARRAY_LANES

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
    """Emits code for a body over `lanes` comprehension indices at once.

    A K-lane value is a list of `groups` SSA names, each a <width x T> vector
    holding lanes g*width .. g*width+width-1, and every operation is emitted
    once per group. With width == lanes there is one group (one <K x T>
    vector). Linux AArch64 uses width 2, one NEON register of f64/i64, so
    every mask is the compare result of one register: LLVM splits a wider
    vector across registers and keeps masks that span the split as bytes,
    widening them again for every 64-bit select or zext.
    """
    def __init__(self, gen, fb, fns: Dict[str, S.Fn], lanes=None, width=None):
        self.gen = gen; self.fb = fb; self.fns = fns
        self.lanes = K if lanes is None else lanes
        self.width = (WIDTH if lanes is None else self.lanes) if width is None else width
        assert self.lanes % self.width == 0
        self.groups = self.lanes // self.width
        self.mask = None

    def each(self, text, ty, *values):
        """One instruction per group; `text` maps the groups' operands to it."""
        return [self.fb.ins(text(*(v[g] for v in values)), ty).name for g in range(self.groups)]

    def checked(self, operation, a, b, node):
        W = self.width
        vt = f'<{W} x i64>'
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
        if not self.gen.checked_integer() or getattr(node,'arithmetic_proven',False) or safe:
            return self.each(lambda x, y: f'{operation} {vt} {x}, {y}', vt, a, b)
        if self.mask:
            a=self.each(lambda m, x: f'select <{W} x i1> {m}, {vt} {x}, {vt} zeroinitializer', vt, self.mask, a)
            b=self.each(lambda m, x: f'select <{W} x i1> {m}, {vt} {x}, {vt} zeroinitializer', vt, self.mask, b)
        ty=f'{{ {vt}, <{W} x i1> }}'
        result=self.each(lambda x, y: f'call {ty} @llvm.s{operation}.with.overflow.v{W}i64({vt} {x}, {vt} {y})', ty, a, b)
        value=self.each(lambda r: f'extractvalue {ty} {r}, 0', vt, result)
        bad=self.each(lambda r: f'extractvalue {ty} {r}, 1', f'<{W} x i1>', result)
        self.check_mask(bad,node)
        return value

    def any_lane(self, masks):
        """i1: some lane of the K-lane mask is set."""
        W = self.width
        part = masks[0]
        for other in masks[1:]: part = self.fb.ins(f'or <{W} x i1> {part}, {other}', f'<{W} x i1>').name
        return self.fb.ins(f"call i1 @llvm.vector.reduce.or.v{W}i1(<{W} x i1> {part})", "i1")

    def check_mask(self, bad, node):
        W = self.width
        if self.mask:bad=self.each(lambda x, m: f'and <{W} x i1> {x}, {m}', f'<{W} x i1>', bad, self.mask)
        self.gen.trap_if(self.any_lane(bad),node,'integer vector overflow')

    def vty(self, t) -> str:
        W = self.width
        return {S.I64: f"<{W} x i64>", S.F64: f"<{W} x double>", S.BOOL: f"<{W} x i1>"}[t]

    def splat(self, scalar: str, ty: str, t) -> List[str]:
        W = self.width
        fb = self.fb
        a = fb.ins(f"insertelement {self.vty(t)} poison, {ty} {scalar}, i64 0", self.vty(t))
        return [fb.ins(f"shufflevector {a}, {self.vty(t)} poison, <{W} x i32> zeroinitializer", self.vty(t)).name] * self.groups

    def const(self, val: str, t) -> str:
        W = self.width
        ty = {S.I64: "i64", S.F64: "double", S.BOOL: "i1"}[t]
        return "<" + ", ".join(f"{ty} {val}" for _ in range(W)) + ">"

    def consts(self, val: str, t) -> List[str]:
        return [self.const(val, t)] * self.groups

    def offsets(self) -> List[str]:
        """Per group, the <width x i64> lane numbers of that group."""
        W = self.width
        return ['<' + ', '.join(f'i64 {g*W+k}' for k in range(W)) + '>' for g in range(self.groups)]

    def gen_vec(self, e: S.Node, venv: Dict[str, List[str]], senv) -> List[str]:
        """venv: name -> per-group vector SSA names; senv: scalar env (Slots) for captured outer variables."""
        W = self.width
        fb = self.fb
        vt = self.vty(e.ty)
        each = self.each
        if isinstance(e, S.Num): return self.consts(str(e.value), S.I64)
        if isinstance(e, S.Flt):
            from .llvm import fconst
            return self.consts(fconst(e.value), S.F64)
        if isinstance(e, S.BoolLit): return self.consts("true" if e.value else "false", S.BOOL)
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
            scalar = 'i64' if e.ty == S.I64 else 'double'
            loads = []
            for g in range(self.groups):
                index = fb.ins(f'add i64 {base}, {offset + g*W}', 'i64')
                ptr = fb.ins(f'getelementptr inbounds {scalar}, ptr {data.name}, i64 {index.name}', 'ptr')
                loads.append(fb.ins(f'load {vt}, ptr {ptr.name}, align 8',vt).name)
            return loads
        if isinstance(e, S.Bin):
            a = self.gen_vec(e.left, venv, senv)
            lt = e.left.ty; lvt = self.vty(lt)
            true, false = self.const("true",S.BOOL), self.const("false",S.BOOL)
            if e.op in ("&&", "||"):
                previous=self.mask
                rhs_mask=a if e.op=='&&' else each(lambda x: f'xor {lvt} {x}, {true}',lvt,a)
                self.mask=rhs_mask if previous is None else each(lambda p, r: f'and {lvt} {p}, {r}',lvt,previous,rhs_mask)
                b=self.gen_vec(e.right,venv,senv);self.mask=previous
                if e.op=='&&': return each(lambda x, y: f'select {lvt} {x}, {lvt} {y}, {lvt} {false}',vt,a,b)
                return each(lambda x, y: f'select {lvt} {x}, {lvt} {true}, {lvt} {y}',vt,a,b)
            b = self.gen_vec(e.right, venv, senv)
            fl = lt == S.F64
            if e.op in ("+", "-", "*", "/", "%"):
                op = {"+": "fadd" if fl else "add", "-": "fsub" if fl else "sub", "*": "fmul" if fl else "mul",
                      "/": "fdiv" if fl else "sdiv", "%": "srem"}[e.op]
                if not fl and e.op in ('+','-','*'):return self.checked(op,a,b,e)
                if e.op == '%' and not fl:
                    from .llvm import Val
                    reduced = [self.gen.bounded_remainder(e, Val(x,lvt), Val(y,lvt), lanes=W) for x, y in zip(a, b)]
                    if reduced[0] is not None: return [r.name for r in reduced]
                if not fl and self.gen.checked_integer():
                    if self.mask:
                        a=each(lambda m, x: f'select <{W} x i1> {m}, {lvt} {x}, {lvt} zeroinitializer',lvt,self.mask,a)
                        b=each(lambda m, x: f'select <{W} x i1> {m}, {lvt} {x}, {lvt} {self.const("1",S.I64)}',lvt,self.mask,b)
                    minval=self.const('-9223372036854775808',S.I64);minus=self.const('-1',S.I64)
                    first=each(lambda x: f'icmp eq {lvt} {x}, {minval}',f'<{W} x i1>',a)
                    second=each(lambda y: f'icmp eq {lvt} {y}, {minus}',f'<{W} x i1>',b)
                    bad=each(lambda x, y: f'and <{W} x i1> {x}, {y}',f'<{W} x i1>',first,second);self.check_mask(bad,e)
                return each(lambda x, y: f"{op} {lvt} {x}, {y}", vt, a, b)
            if fl:
                op = {"<": "olt", "<=": "ole", ">": "ogt", ">=": "oge", "==": "oeq", "!=": "une"}[e.op]
                return each(lambda x, y: f"fcmp {op} {lvt} {x}, {y}", vt, a, b)
            op = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "eq", "!=": "ne"}[e.op]
            return each(lambda x, y: f"icmp {op} {lvt} {x}, {y}", vt, a, b)
        if isinstance(e, S.Un):
            if e.op=='-' and isinstance(e.expr,S.Num) and e.expr.value==1<<63:return self.consts('-9223372036854775808',S.I64)
            a = self.gen_vec(e.expr, venv, senv)
            if e.op == "!": return each(lambda x: f"xor {vt} {x}, {self.const('true', S.BOOL)}", vt, a)
            if e.ty == S.F64: return each(lambda x: f"fneg {vt} {x}", vt, a)
            return self.checked('sub',['zeroinitializer']*self.groups,a,e)
        if isinstance(e, S.Cast):
            a = self.gen_vec(e.expr, venv, senv)
            if e.to == S.F64: return each(lambda x: f"sitofp <{W} x i64> {x} to <{W} x double>", vt, a)
            if self.mask:a=each(lambda m, x: f'select <{W} x i1> {m}, <{W} x double> {x}, <{W} x double> zeroinitializer',f'<{W} x double>',self.mask,a)
            from .llvm import fconst
            low=each(lambda x: f'fcmp oge <{W} x double> {x}, {self.const(fconst(float(-(1<<63))),S.F64)}',f'<{W} x i1>',a)
            high=each(lambda x: f'fcmp olt <{W} x double> {x}, {self.const(fconst(float(1<<63)),S.F64)}',f'<{W} x i1>',a)
            good=each(lambda x, y: f'and <{W} x i1> {x}, {y}',f'<{W} x i1>',low,high)
            bad=each(lambda x: f'xor <{W} x i1> {x}, {self.const("true",S.BOOL)}',f'<{W} x i1>',good);self.check_mask(bad,e)
            return each(lambda x: f"fptosi <{W} x double> {x} to <{W} x i64>", vt, a)
        if isinstance(e, S.Let):
            v = self.gen_vec(e.value, venv, senv)
            v2 = dict(venv); v2[e.name] = v
            return self.gen_vec(e.body, v2, senv)
        if isinstance(e, S.If):
            c = self.gen_vec(e.cond, venv, senv)
            previous=self.mask
            self.mask=c if previous is None else each(lambda p, x: f'and <{W} x i1> {p}, {x}',f'<{W} x i1>',previous,c)
            a = self.gen_vec(e.then, venv, senv)
            inverse=each(lambda x: f'xor <{W} x i1> {x}, {self.const("true",S.BOOL)}',f'<{W} x i1>',c)
            self.mask=inverse if previous is None else each(lambda p, x: f'and <{W} x i1> {p}, {x}',f'<{W} x i1>',previous,inverse)
            b = self.gen_vec(e.els, venv, senv)
            self.mask=previous
            return each(lambda x, y, z: f"select <{W} x i1> {x}, {vt} {y}, {vt} {z}", vt, c, a, b)
        if isinstance(e, S.Call):
            if getattr(e, "builtin", None) == "sqrt":
                a = self.gen_vec(e.args[0], venv, senv)
                return each(lambda x: f"call <{W} x double> @llvm.sqrt.v{W}f64(<{W} x double> {x})", vt, a)
            f = self.fns[e.name]
            v2 = dict(venv)
            for p, a in zip(f.params, e.args):
                v2[p.name] = self.gen_vec(a, venv, senv)         # inline: parameters become lane vectors
            return self.gen_vec(f.body, v2, senv)
        if isinstance(e, S.Loop):
            return self.gen_loop(e, venv, senv)
        raise TypeError(type(e))

    def gen_loop(self, e: S.Loop, venv, senv) -> List[str]:
        """Masked loop: run while any lane's condition holds; finished lanes keep their state.

        Each iteration is one block that evaluates the condition, then the
        successor under the resulting mask. The mask is recomputed from the
        state instead of being carried: a finished lane's frozen state is the
        one its condition last failed on, with the same checks passing, so it
        keeps failing. A carried <K x i1> phi is a byte vector on AArch64. The
        successor is evaluated once more after the last lane finishes, fully
        masked, and discarded.
        """
        W = self.width
        fb = self.fb
        tys = [self.vty(t) for t in e.state_tys]
        ptrs = []
        for x, ty in zip(e.inits, tys):
            ps = []
            for v in self.gen_vec(x, venv, senv):
                p = fb.alloca(ty); fb.store(_V(v, ty), p); ps.append(p)
            ptrs.append(ps)
        parent_mask=self.mask
        body, exit_ = fb.label("vloop_body"), fb.label("vloop_exit")
        fb.br(body); fb.block(body)
        v2 = dict(venv)
        for n, ps, ty in zip(e.names, ptrs, tys): v2[n] = [fb.load(ty, p).name for p in ps]
        c = self.gen_vec(e.cond, v2, senv)
        m2 = c if parent_mask is None else self.each(lambda p, x: f"and <{W} x i1> {p}, {x}", f"<{W} x i1>", parent_mask, c)
        self.mask = m2
        nexts = [self.gen_vec(x, v2, senv) for x in e.nexts]
        for n, ps, ty, nx in zip(e.names, ptrs, tys, nexts):
            for p, sel in zip(ps, self.each(lambda m, x, y: f"select <{W} x i1> {m}, {ty} {x}, {ty} {y}", ty, m2, nx, v2[n])):
                fb.store(_V(sel, ty), p)
        fb.cbr(self.any_lane(m2), body, exit_); fb.block(exit_)
        v3 = dict(venv)
        for n, ps, ty in zip(e.names, ptrs, tys): v3[n] = [fb.load(ty, p).name for p in ps]
        self.mask = parent_mask
        return self.gen_vec(e.yld, v3, senv)

class _V:
    """Minimal stand-in for llvm.Val (name, ty) to reuse FuncBuilder.store."""
    def __init__(self, name, ty): self.name = name; self.ty = ty
    def __str__(self): return f"{self.ty} {self.name}"

S_TOP = (-(1 << 63), (1 << 63)-1)

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
    head,body,end=fb.label('varr_cond'),fb.label('varr_body'),fb.label('varr_end')
    fb.br(head);fb.block(head)
    i=fb.load('i64',ip)
    remaining=fb.ins(f'sub i64 {upper.name}, {i.name}','i64')
    fb.cbr(fb.ins(f'icmp sge i64 {remaining.name}, {K}','i1'),body,end);fb.block(body)
    vg=VecGen(gen,fb,gen.fn_map,lanes=K,width=ARRAY_WIDTH);vg.array_index=(e.var,i.name)
    base=vg.splat(i.name,'i64',S.I64)
    lanes=vg.each(lambda b, o: f'add <{vg.width} x i64> {b}, {o}',f'<{vg.width} x i64>',base,vg.offsets())
    value=vg.gen_vec(e.body,{e.var:lanes},env)
    data=fb.ins(f'extractvalue {out}, 0','ptr')
    index=fb.ins(f'sub i64 {i.name}, {origin.name}','i64')
    scalar_ty='i64' if e.ty.elem==S.I64 else 'double'
    for g, v in enumerate(value):
        at=fb.ins(f'add i64 {index.name}, {g*vg.width}','i64')
        ptr=fb.ins(f'getelementptr inbounds {scalar_ty}, ptr {data.name}, i64 {at.name}','ptr')
        fb.emit(f'store {vg.vty(e.ty.elem)} {v}, ptr {ptr.name}, align 8')
    fb.store(fb.ins(f'add i64 {i.name}, {K}','i64'),ip);fb.br(head);fb.block(end)
    gen.counted_loop(fb.load('i64',ip),hi,e.var,env,scalar)

def vector_sum_loop(gen, fb, e: S.Sum, lo, hi, env, acc_ptr: str, fns: Dict[str, S.Fn]):
    """Accumulate sum(body) over [lo, hi) into *acc_ptr, K lanes at a time.

    Whole vectors run the body unmasked; one masked iteration takes the tail,
    its inactive lanes recomputing the last valid index.
    """
    vg = VecGen(gen, fb, fns)
    W = vg.width
    t = e.ty; vt = vg.vty(t)
    each = vg.each
    vacc = []
    for g in range(vg.groups):
        p = fb.alloca(vt); fb.store(_V("zeroinitializer", vt), p); vacc.append(p)
    ip = fb.alloca("i64"); fb.store(_V(lo.name, "i64"), ip)
    def accumulate(val, active):
        old = [fb.load(vt, p).name for p in vacc]
        if t == S.I64:
            summed = vg.checked('add', old, val, e)
            if active: summed = each(lambda m, x, y: f'select <{W} x i1> {m}, {vt} {x}, {vt} {y}', vt, active, summed, old)
        else:
            summed = each(lambda x, y: f"fadd reassoc {vt} {x}, {y}", vt, old, val)
        for p, s in zip(vacc, summed): fb.store(_V(s, vt), p)
    cond, body, tail = fb.label("vsum_full_cond"), fb.label("vsum_full_body"), fb.label("vsum_tail")
    fb.br(cond); fb.block(cond)
    i = fb.load("i64", ip)
    remaining = fb.ins(f'sub i64 {hi.name}, {i.name}','i64')
    fb.cbr(fb.ins(f'icmp sge i64 {remaining.name}, {K}','i1'), body, tail); fb.block(body)
    lanes = each(lambda b, o: f"add <{W} x i64> {b}, {o}", f"<{W} x i64>", vg.splat(i.name, 'i64', S.I64), vg.offsets())
    vg.mask = None
    accumulate(vg.gen_vec(e.body, {e.var: lanes}, env), None)
    fb.store(fb.ins(f'add i64 {i.name}, {K}','i64'),ip)
    fb.br(cond); fb.block(tail)
    i = fb.load("i64", ip)
    last_body, end = fb.label("vsum_last"), fb.label("vsum_end")
    fb.cbr(fb.ins(f"icmp slt i64 {i.name}, {hi.name}", "i1"), last_body, end); fb.block(last_body)
    lanes = each(lambda b, o: f"add <{W} x i64> {b}, {o}", f"<{W} x i64>", vg.splat(i.name, 'i64', S.I64), vg.offsets())
    remaining = fb.ins(f'sub i64 {hi.name}, {i.name}','i64')
    remainv = vg.splat(remaining.name,'i64',S.I64)
    active = each(lambda o, r: f"icmp slt <{W} x i64> {o}, {r}", f"<{W} x i1>", vg.offsets(), remainv)
    last = fb.ins(f"sub i64 {hi.name}, 1", "i64")
    lastv = vg.splat(last.name, "i64", S.I64)
    idx = each(lambda m, x, y: f"select <{W} x i1> {m}, <{W} x i64> {x}, <{W} x i64> {y}", f"<{W} x i64>", active, lanes, lastv)
    vg.mask = active                              # inactive lanes recompute the last valid index and are masked out
    val = vg.gen_vec(e.body, {e.var: idx}, env)
    accumulate(each(lambda m, x: f"select <{W} x i1> {m}, {vt} {x}, {vt} zeroinitializer", vt, active, val), active)
    vg.mask = None
    fb.br(end); fb.block(end)
    v = [fb.load(vt, p).name for p in vacc]
    if t == S.F64:
        total = v[0]
        for other in v[1:]: total = fb.ins(f"fadd reassoc {vt} {total}, {other}", vt).name
        red = fb.ins(f"call reassoc double @llvm.vector.reduce.fadd.v{W}f64(double 0.0, {vt} {total})", "double")
        old = fb.load("double", acc_ptr); fb.store(fb.ins(f"fadd reassoc double {old.name}, {red.name}", "double"), acc_ptr)
    else:
        old=fb.load('i64',acc_ptr)
        for part in v:
            for lane in range(W):
                value=fb.ins(f'extractelement {vt} {part}, i64 {lane}','i64')
                old=gen.checked_operation('+',old,value,e) if gen.checked_integer() else fb.ins(f'add {old}, {value.name}','i64')
        fb.store(old,acc_ptr)
