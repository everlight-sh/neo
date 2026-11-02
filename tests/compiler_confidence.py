#!/usr/bin/env python3
"""Generated-program/optimizer equivalence and arithmetic boundary checks."""
import json
import os
import platform
from pathlib import Path
import random
import shlex
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from neoc import syntax as S
from neoc.reference import Reference

BUILD_ID=os.environ.get('NEO_TARGET') or platform.system().lower()+'-'+platform.machine()
OUT=ROOT/'.kernel-build/usability/confidence'/BUILD_ID;RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))

def build(source,name,env=None):
    binary=OUT/name
    r=subprocess.run([sys.executable,'-m','neoc','build',str(source),'-o',str(binary),'--report'],cwd=ROOT,
        capture_output=True,text=True,env={**os.environ,**(env or {})})
    (OUT/(name+'-build.json')).write_text(r.stdout+r.stderr)
    assert r.returncode==0,r.stdout[-6000:]+r.stderr
    assert not json.loads(r.stdout)['undefined_symbols']
    return binary

def execute(binary,args,env=None):
    return subprocess.run(RUNNER+[str(binary),*map(str,args)],capture_output=True,text=True,timeout=30,env={**os.environ,'NEO_THREADS':'1',**(env or {})})

def boundaries():
    binary=build(ROOT/'tests/fixtures/integers.neo','integers')
    minimum=-(1<<63);maximum=(1<<63)-1
    success=[([0,maximum,-1],maximum-1),([1,minimum,-1],minimum+1),([2,-7,3],-21),([3,-7,3],-2),([4,-7,3],-1),
        ([3,minimum,1],minimum),([5,maximum,1],minimum),([8,maximum,0],2),([12,maximum,0],2),([13,maximum,0],2),([14,0,0],2),([15,0,0],2),([16,0,0],528)]
    failure=[[0,maximum,1],[1,minimum,1],[2,maximum,2],[3,minimum,-1],[4,minimum,-1],[6,maximum,0],[7,maximum,0],[9,0,0],[10,minimum,0],[11,maximum,0],[17,maximum,0],[18,0,0]]
    for args,value in success:
        r=execute(binary,args);assert r.returncode==0 and int(r.stdout)==value,(args,r.stdout,r.stderr)
    for args in failure:
        for threads in ('1','4'):
            r=execute(binary,args,{'NEO_THREADS':threads});assert r.returncode!=0 and ('overflow' in r.stderr or 'out of range' in r.stderr),(args,r.returncode,r.stdout,r.stderr)
    print('PASS checked integer arithmetic, explicit wrapping, division, reduction, SIMD masks, folding and float-cast boundaries',flush=True)

def generated():
    rng=random.Random(20261024)
    def expression(depth):
        if depth==0:return rng.choice(['x',str(rng.randrange(-30,31))])
        op=rng.choice(['+','-','*','/','%','if'])
        a=expression(depth-1)
        if op=='if':return f'(if x < {rng.randrange(-10,11)} then {a} else {expression(depth-1)})'
        b=str(rng.randrange(1,18)) if op in ('/','%') else expression(depth-1)
        return f'({a} {op} {b})'
    definitions=[f'fn case_{i} (x: i64) -> i64 = {expression(3)}' for i in range(80)]
    dispatch='case_79(x)'
    for i in reversed(range(79)):dispatch=f'if which == {i} then case_{i}(x) else {dispatch}'
    source='\n'.join(definitions)+'\nfn main (which: i64,x: i64) -> i64 = '+dispatch+'\n'
    file=OUT/'generated.neo';file.write_text(source)
    program=S.parse(source)
    modes=[({},'optimized'),({'NEO_VEC':'0','NEO_FOLD':'0','NEO_INLINE':'0','NEO_RANGE':'0'},'baseline')]
    values=[-100,-1,0,1,97]
    expected={(i,x):Reference(program).call(f'case_{i}',[x]) for i in range(80) for x in values}
    for env,name in modes:
        binary=build(file,name,env)
        for (i,x),value in expected.items():
            r=execute(binary,[i,x]);assert r.returncode==0 and int(r.stdout)==value,(name,i,x,value,r.returncode,r.stdout,r.stderr)
    (OUT/'generated-expected.json').write_text(json.dumps({f'{i}:{x}':v for (i,x),v in expected.items()}))
    print('PASS 80 generated programs × 5 inputs × 2 optimization modes against an independent evaluator',flush=True)

def parser_fuzz():
    rng=random.Random(840024)
    alphabet='fn main () -> i64 = 0123456789{}[]:+-*/";\nabcdefghijklmnopqrstuvwxyz'
    for i in range(2000):
        text=''.join(rng.choice(alphabet) for _ in range(rng.randrange(1,200)))
        try:S.parse(text)
        except (S.SyntaxError_,RecursionError,ValueError):pass
    print('PASS 2000 deterministic malformed-source parser fuzz inputs without internal crashes',flush=True)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    boundaries();generated();parser_fuzz()

if __name__=='__main__':main()
