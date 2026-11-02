#!/usr/bin/env python3
"""The 40-opcode VM fixture against an independent Python model, and its
dispatch lowered to one LLVM switch (a jump table on x86-64/ARM64)."""
import json,os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build,ROOT

M=(1<<64)-1
def s64(x):
    x&=M;return x-(1<<64) if x>>63 else x

def program():
    code=[]
    for at in range(64):
        code.append((at*7+3)%38 if at<62 else 38 if at==62 else 39)
        code.append(0 if at==62 else (at*13+5)%17+1)
    return code

def run(iterations):
    code=program();mem=[i*3 for i in range(64)]
    pc,a,b,c,d,k=0,1,2,3,4,iterations
    fetch=lambda p:code[p] if 0<=p<len(code) else 39
    cell=lambda i:mem[i&63]
    while pc>=0:
        op,arg=fetch(pc),fetch(s64(pc+1));n=s64(pc+2)
        if op==24:mem[arg&63]=a
        elif op==26:mem[b&63]=c
        if op==0:pc=n
        elif op==1:pc,a=n,s64(a+arg)
        elif op==2:pc,a=n,s64(a-arg)
        elif op==3:pc,a=n,s64(a*arg)
        elif op==4:pc,a=n,a^arg
        elif op==5:pc,a=n,a&s64(arg*1023)
        elif op==6:pc,a=n,a|arg
        elif op==7:pc,a=n,s64(a<<(arg&63))
        elif op==8:pc,a=n,s64((a&M)>>(arg&63))
        elif op==9:pc,a=n,s64(a+b)
        elif op==10:pc,a=n,s64(a-b)
        elif op==11:pc,a=n,s64(a*(b|1))
        elif op==12:pc,a=n,a^b
        elif op==13:pc,a=n,a&(b|255)
        elif op==14:pc,a=n,a|(b&65535)
        elif op==15:pc,b=n,a
        elif op==16:pc,c=n,a
        elif op==17:pc,a=n,c
        elif op==18:pc,a,b=n,b,a
        elif op==19:pc,c=n,s64(c+1)
        elif op==20:pc,c=n,s64(c-1)
        elif op==21:pc,b=n,s64(b+c)
        elif op==22:pc,b=n,b^c
        elif op==23:pc,a=n,s64(a+cell(arg))
        elif op in (24,26):pc=n
        elif op==25:pc,b=n,b^cell(a)
        elif op==27:pc,a=n,s64(-a)
        elif op==28:pc,a=n,a^-1
        elif op==29:
            r=arg&63;pc,a=n,s64(((a&M)<<r)|((a&M)>>((64-r)&63)))
        elif op==30:pc,a=n,max(a,b)
        elif op==31:pc,a=n,min(a,b)
        elif op==32:pc,a=n,s64(a+b*arg)
        elif op==33:pc,c=n,c^a
        elif op==34:pc,d=n,s64(d+1)
        elif op==35:pc,a=n,s64(b+c)
        elif op==36:pc,b=n,a^d
        elif op==37:pc,c=n,s64(((a&M)>>3)+b)
        elif op==38:
            k=s64(k-1);pc=arg if k>0 else n
        else:pc=-1
    return s64(a^b^c^s64(d+sum(x&65535 for x in mem)))

def main():
    with tempfile.TemporaryDirectory(prefix='neo-opcode-vm-') as temp:
        binary=Path(temp)/'vm';build('tests/fixtures/opcode_vm.neo',binary)
        for iterations in [0,1,2,3,10,257,5000]:
            result=subprocess.run(RUNNER+[str(binary),str(iterations)],capture_output=True,text=True,timeout=60)
            assert result.returncode==0 and result.stdout==str(run(iterations))+'\n',(iterations,result.stdout,run(iterations),result.stderr)
        ir=subprocess.run(['python3','-m','neoc','build','tests/fixtures/opcode_vm.neo','--emit-llvm'],cwd=ROOT,capture_output=True,text=True,check=True).stdout
        start=ir.index('_step__par(');step=ir[start:ir.index('\n}',start)]
        # One switch on the opcode with a case per opcode, before LLVM runs.
        assert step.count('switch i64')==1 and step.count(', label %')>=39,step[:400]
    print('PASS 40-opcode VM: native results match the Python model; dispatch is one 40-case switch',flush=True)

if __name__=='__main__':main()
