"""Stack switch ABI for cooperative Neo tasks; no C or host thread runtime.

Only callee-saved registers cross a switch. A task resumes at an ordinary call
return, with its original stack and resource cleanup frames still live.
ABI references: https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst
https://gitlab.com/x86-psABIs/x86-64-ABI/-/blob/master/x86-64-ABI/low-level-sys-info.tex
"""
def assembly(triple):
    darwin='apple' in triple
    prefix='_' if darwin else ''
    public=lambda name:('\n.globl '+prefix+name+'\n'+('.private_extern '+prefix+name if darwin else '.hidden '+name)+'\n'+prefix+name+':\n')
    arm=triple.startswith(('arm64','aarch64'))
    code='.text\n.p2align 4\n'+public('ax_fiber_swap')
    if arm:
        code+='''stp x19, x20, [x0, #0]
stp x21, x22, [x0, #16]
stp x23, x24, [x0, #32]
stp x25, x26, [x0, #48]
stp x27, x28, [x0, #64]
stp x29, x30, [x0, #80]
mov x9, sp
str x9, [x0, #96]
stp d8, d9, [x0, #104]
stp d10, d11, [x0, #120]
stp d12, d13, [x0, #136]
stp d14, d15, [x0, #152]
mrs x9, fpcr
str x9, [x0, #168]
mrs x9, fpsr
str x9, [x0, #176]
ldp x19, x20, [x1, #0]
ldp x21, x22, [x1, #16]
ldp x23, x24, [x1, #32]
ldp x25, x26, [x1, #48]
ldp x27, x28, [x1, #64]
ldp x29, x30, [x1, #80]
ldr x9, [x1, #96]
mov sp, x9
ldp d8, d9, [x1, #104]
ldp d10, d11, [x1, #120]
ldp d12, d13, [x1, #136]
ldp d14, d15, [x1, #152]
ldr x9, [x1, #168]
msr fpcr, x9
ldr x9, [x1, #176]
msr fpsr, x9
ret
'''+public('ax_fiber_init')+'''str x3, [x0, #0]
str x2, [x0, #8]
adr x9, Lneo_fiber_boot
str x9, [x0, #88]
str x1, [x0, #96]
ret
Lneo_fiber_boot:
mov x0, x19
blr x20
brk #0
'''
    else:
        code+='''movq %rbx, 0(%rdi)
movq %rbp, 8(%rdi)
movq %r12, 16(%rdi)
movq %r13, 24(%rdi)
movq %r14, 32(%rdi)
movq %r15, 40(%rdi)
leaq 8(%rsp), %rax
movq %rax, 48(%rdi)
movq (%rsp), %rax
movq %rax, 56(%rdi)
stmxcsr 64(%rdi)
fnstcw 68(%rdi)
movq 0(%rsi), %rbx
movq 8(%rsi), %rbp
movq 16(%rsi), %r12
movq 24(%rsi), %r13
movq 32(%rsi), %r14
movq 40(%rsi), %r15
ldmxcsr 64(%rsi)
fldcw 68(%rsi)
movq 48(%rsi), %rsp
jmpq *56(%rsi)
'''+public('ax_fiber_init')+'''movq %rcx, 16(%rdi)
movq %rdx, 24(%rdi)
movq %rsi, 48(%rdi)
leaq Lneo_fiber_boot(%rip), %rax
movq %rax, 56(%rdi)
movl $8064, 64(%rdi)
movw $895, 68(%rdi)
retq
Lneo_fiber_boot:
movq %r12, %rdi
callq *%r13
ud2
'''
    return ['module asm "'+code.strip().replace('\n','\\0A')+'"',
            'declare hidden void @ax_fiber_swap(ptr, ptr)',
            'declare hidden void @ax_fiber_init(ptr, ptr, ptr, ptr)']
