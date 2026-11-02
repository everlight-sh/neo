#!/usr/bin/env python3
"""mkvariants.py OUTDIR : variant files of the current checkout with some of my r2/r3 changes reverted.
OUTDIR/<variant>/<path> overlays the current tree. 'before' reverts all of them."""
import subprocess, sys
from pathlib import Path
A = Path(__file__).resolve().parents[5]; out = Path(sys.argv[1])
head = lambda p: subprocess.check_output(['git', '-C', str(A), 'show', f'HEAD:{p}'], text=True)
cur = lambda p: (A / p).read_text()
def rep(s, old, new):
    assert s.count(old) == 1, old[:80]; return s.replace(old, new)
# http_uring.ax: receive hunk only
recv_new = cur('runtime/http_uring.ax')
i = recv_new.index('; IORING_OP_RECV into the free input tail, attempted'); j = recv_new.index('effect fn rt_uring_recv')
pollfirst = recv_new[:i] + """; IORING_OP_RECV into the free input tail. It waits for readiness before its
; first attempt (ioprio IORING_RECVSEND_POLL_FIRST): a receive follows a sent
; response or a new connection, so an immediate attempt would usually fail.
; Measured: 0.25 us less server CPU per request than attempting first.
""" + recv_new[j:]
pollfirst = rep(pollfirst, "rt_uring_push(d, 27, load_i64(state, 0),", "rt_uring_push(d, bit_or(27, shift_left(1, 16)), load_i64(state, 0),")
# http_uring.ax: accept hunk only
h = head('runtime/http_uring.ax')
old_acc = h[h.index('  = if user == 0 then\n'):h.index('    else if user == 1 then')]
c = cur('runtime/http_uring.ax')
new_acc = c[c.index('  = if user == 0 then\n'):c.index('    else if user == 1 then')]
accept1 = rep(c, new_acc, old_acc)
# llvm.py: private heap preset, bounded sums
l = cur('axonc/llvm.py')
i = l.index('        # Managed arrays need shared pages only for the allocating fork'); j = l.index("        omitted = {bodies[name] for name in self.omitted_functions}")
l = l[:i] + l[j:]
l = rep(l, '                f"@ax_default_heap_mode = internal constant i64 {1 if self.private_heap else 0}",\n', '')
l = rep(l, """        # Heap mode preset before the runtime selects its small allocator:
        # @ax_default_heap_mode is defined after reachability pruning (program()).
        mode_slot = fb.ins('getelementptr i8, ptr @ax_runtime_state, i64 184','ptr')
        fb.store(fb.load('i64','@ax_default_heap_mode'),mode_slot.name)
""", '')
l = rep(l, "    def add_vals(self, a: Val, b: Val, t, node=None) -> Val:", "    def add_vals(self, a: Val, b: Val, t) -> Val:")
l = rep(l, """            # A sum whose accumulation is bounded (sum_bounded) cannot overflow.
            if isinstance(node,S.Sum) and getattr(node,'arithmetic_proven',False): return fb.ins(f"add nsw {a}, {b.name}", "i64")
""", '')
i = l.index('    def sum_bounded(self, e):'); j = l.index('    def comprehension(self, e, env, par):')
l = l[:i] + l[j:]
l = rep(l, """        # The vectorized sum loop reads the same mark for its lane additions.
        if is_sum and e.ty == S.I64 and self.sum_bounded(e): e.arithmetic_proven = True
""", '')
assert l.count(', e.ty, e), ') == 3; l = l.replace(', e.ty, e), ', ', e.ty), ')
for w in ('private_heap', 'sum_bounded', 'ax_default_heap_mode', 'node=None'): assert w not in l, w
# cli.py: loop alignment
k = cur('axonc/cli.py')
i = k.index("    # x86-64: start every loop on a 32-byte boundary"); j = k.index("    if 'apple' in target:")
cli = k[:i] + k[j:]
core = {p: head(p) for p in ('runtime/core.ax', 'runtime/platform_linux.ax', 'runtime/platform_linux_x86_64.ax', 'runtime/platform_macos.ax')}
V = {
    'pollfirst': {'runtime/http_uring.ax': pollfirst},
    'accept1': {'runtime/http_uring.ax': accept1, 'runtime/http_linux.ax': head('runtime/http_linux.ax')},
    'nocore': core,
    'noalign': {'axonc/cli.py': cli},
    'nollvm': {'axonc/llvm.py': l},
    'before': {**core, 'runtime/http_uring.ax': head('runtime/http_uring.ax'), 'runtime/http_linux.ax': head('runtime/http_linux.ax'),
               'axonc/llvm.py': l, 'axonc/cli.py': cli},
}
for name, files in V.items():
    for p, text in files.items():
        f = out / name / p; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text)
    print(name, sorted(files))
