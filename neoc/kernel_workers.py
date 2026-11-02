"""Persistent Linux worker threads, with Neo-owned scheduling and stacks.

The raw clone returns on a different stack in the child, so this boundary
cannot be expressed as an ordinary LLVM call followed by Neo instructions.
ABI: ax_spawn_thread(pool, 16-byte-aligned stack top). Workers are real
threads (CLONE_THREAD), so the program's exit_group ends them and a trap in
any worker ends the process. Each worker sleeps on the pool generation futex;
for every published job it claims chunks from the shared counter with an
atomic fetch-add, then decrements the pending count and wakes the parent at 0.
Pool layout (bytes): 0 generation (futex word), 8 region function, 16 context,
24 next chunk, 32 end chunk, 40 pending workers (futex word).
https://man7.org/linux/man-pages/man2/clone.2.html
https://man7.org/linux/man-pages/man2/futex.2.html
"""

# CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND | CLONE_THREAD | CLONE_SYSVSEM
CLONE_FLAGS = 0x50f00

def assembly(triple):
    if 'linux' not in triple: return []
    if triple.startswith(('aarch64','arm64')):
        code = '''
.text
.p2align 4
.global ax_spawn_thread
.hidden ax_spawn_thread
.type ax_spawn_thread,%function
ax_spawn_thread:
sub x1, x1, #16
str x0, [x1]
movz x0, #0x0f00
movk x0, #0x5, lsl #16
mov x2, #0
mov x3, #0
mov x4, #0
mov x8, #220
svc #0
cbz x0, .Lax_worker_child
ret
.Lax_worker_child:
ldr x19, [sp]
mov w20, #0
.Lax_worker_wait:
ldar w21, [x19]
cmp w21, w20
b.ne .Lax_worker_job
mov x0, x19
mov x1, #128
mov w2, w20
mov x3, #0
mov x8, #98
svc #0
b .Lax_worker_wait
.Lax_worker_job:
mov w20, w21
ldr x22, [x19, #8]
ldr x23, [x19, #16]
ldr x24, [x19, #32]
add x25, x19, #24
.Lax_worker_claim:
ldaxr x9, [x25]
add x10, x9, #1
stlxr w11, x10, [x25]
cbnz w11, .Lax_worker_claim
cmp x9, x24
b.ge .Lax_worker_done
mov x0, x23
mov x1, x9
blr x22
b .Lax_worker_claim
.Lax_worker_done:
add x26, x19, #40
.Lax_worker_release:
ldaxr x9, [x26]
sub x10, x9, #1
stlxr w11, x10, [x26]
cbnz w11, .Lax_worker_release
cbnz x10, .Lax_worker_wait
mov x0, x26
mov x1, #129
mov x2, #1
mov x8, #98
svc #0
b .Lax_worker_wait
.size ax_spawn_thread, .-ax_spawn_thread
'''
    else:
        code = '''
.text
.p2align 4
.global ax_spawn_thread
.hidden ax_spawn_thread
.type ax_spawn_thread,@function
ax_spawn_thread:
subq $16, %rsi
movq %rdi, 0(%rsi)
movq $0x50f00, %rdi
xorl %edx, %edx
xorl %r10d, %r10d
xorl %r8d, %r8d
movl $56, %eax
syscall
testq %rax, %rax
jz .Lax_worker_child
retq
.Lax_worker_child:
movq 0(%rsp), %rbx
xorl %r12d, %r12d
.Lax_worker_wait:
movl 0(%rbx), %eax
cmpl %r12d, %eax
jne .Lax_worker_job
movq %rbx, %rdi
movl $128, %esi
movl %r12d, %edx
xorl %r10d, %r10d
movl $202, %eax
syscall
jmp .Lax_worker_wait
.Lax_worker_job:
movl %eax, %r12d
movq 8(%rbx), %r13
movq 16(%rbx), %r14
movq 32(%rbx), %r15
.Lax_worker_claim:
movl $1, %esi
lock xaddq %rsi, 24(%rbx)
cmpq %r15, %rsi
jge .Lax_worker_done
movq %r14, %rdi
callq *%r13
jmp .Lax_worker_claim
.Lax_worker_done:
lock decq 40(%rbx)
jnz .Lax_worker_wait
leaq 40(%rbx), %rdi
movl $129, %esi
movl $1, %edx
movl $202, %eax
syscall
jmp .Lax_worker_wait
.size ax_spawn_thread, .-ax_spawn_thread
'''
    return ['module asm "'+code.strip().replace('\n','\\0A')+'"',
            'declare hidden i64 @ax_spawn_thread(ptr, ptr)']


def allocation_free(node, fns, seen=frozenset(), allow_libraries=False):
    """Certify a sequential region body cannot allocate or mutate runtime state.

    Array parameters are borrowed; managed record values/projections, owned
    parameters, array construction/mutation and unknown calls are rejected.
    Scalar reductions and finite unmanaged record operations use stack storage.
    This is a dispatcher safety predicate, not a profitability estimate.
    """
    from . import syntax as S
    def managed(ty):
        return isinstance(ty,S.TArr) or isinstance(ty,S.TRec) and any(managed(t) for _,t in ty.fields)
    if isinstance(node,S.ArrC):return False
    if isinstance(node,(S.RecLit,S.With,S.Index,S.Field)) and managed(node.ty):return False
    if isinstance(node,S.Var) and isinstance(node.ty,S.TRec) and managed(node.ty):return False
    if isinstance(node,S.Loop) and any(managed(t) for t in node.state_tys):return False
    if isinstance(node,S.Sum) and managed(node.ty):return False
    if isinstance(node,S.Call):
        builtin=getattr(node,'builtin',None)
        if builtin:
            if builtin not in ('sqrt','byte_read_le'):return False
        else:
            callee=fns.get(node.name)
            if callee is None or callee.effect or callee.external or callee.exported or getattr(callee,'precompiled',False) or getattr(callee,'native_library',False) and not allow_libraries or callee.name in seen or managed(callee.ret) or any(p.owned or isinstance(p.ty,S.TRec) and managed(p.ty) for p in callee.params):return False
            if not allocation_free(callee.body,fns,seen|{callee.name},allow_libraries):return False
    return all(allocation_free(child,fns,seen,allow_libraries) for child in S.children(node))
