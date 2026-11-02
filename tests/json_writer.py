#!/usr/bin/env python3
"""Structured writer against independent trees and invalid token sequences."""
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
    rng=random.Random(261101);atoms=[None,False,True,0,-1,-2**63,2**63-1,'','\0\n\t"\\é😀',1.25,[1,2],{'ready':True}]
    def value(depth=0):
        if depth>3 or rng.randrange(3)==0:return rng.choice(atoms)
        if rng.randrange(2):return [value(depth+1) for _ in range(rng.randrange(6))]
        return {rng.choice(['','é','\n"\\','field'])+str(i):value(depth+1) for i in range(rng.randrange(6))}
    def ops(v):
        if v is None:return [['null']]
        if isinstance(v,bool):return [['bool',v]]
        if isinstance(v,int):return [['int',v]]
        if isinstance(v,str):return [['string',v]]
        if isinstance(v,float):return [['json',v]]
        if isinstance(v,list):return [['array']]+sum((ops(x) for x in v),[])+[['end_array']]
        return [['object']]+sum(([['key',k]]+ops(x) for k,x in v.items()),[])+[['end_object']]
    cases=[];expected=[]
    for v in atoms+[value() for _ in range(350)]:
        for sequence in [ops(v),[['json',v]]]:
            cases.append({'ops':sequence});expected.append({'ok':True,'value':v,'count':len(v) if isinstance(v,(list,dict)) else 0})
    for depth in range(1,132):
        for leaf in [False,True]:
            cases.append(dict(depth=depth,leaf=leaf))
            if depth>129 or leaf and depth>128:expected.append({'ok':False});continue
            v=7 if leaf else []
            for _ in range(depth if leaf else depth-1):v=[v]
            expected.append(dict(ok=True,value=v,count=1 if leaf or depth>1 else 0))
    invalid=[[],[['end_array']],[['end_object']],[['key','x']],[['array'],['end_object']],[['object'],['int',1]],[['object'],['key','x'],['end_object']],[['object'],['key','x'],['key','y']],[['int',1],['null']],[['missing']],[['array'],['missing'],['end_array']],[['array']],[['object']],[['string_bytes','ff']],[['object'],['key_bytes','c080'],['null'],['end_object']]]
    for sequence in invalid:cases.append(dict(ops=sequence));expected.append({'ok':False})
    cases.append({'ops':[['object'],['key','x'],['int',1],['key','x'],['int',2],['end_object']]});expected.append(dict(ok=True,value={'x':2},count=2))
    with tempfile.TemporaryDirectory(prefix='neo-json-writer-') as tmp:
        binary=Path(tmp)/'writer';build('tests/fixtures/json_writer_probe.neo',binary)
        for workers in [1,4]:
            for start in range(0,len(cases),35):
                batch=cases[start:start+35];data=b''.join(json.dumps(x,ensure_ascii=False).encode().hex().encode()+b'\n' for x in batch)
                run=subprocess.run(RUNNER+[str(binary)],input=data,capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
                assert run.returncode==0,(start,run.stderr)
                actual=[json.loads(x) for x in run.stdout.splitlines()];assert actual==expected[start:start+35],(start,actual,expected[start:start+35])
    print(f'PASS {len(cases)} independent structured JSON writer cases: scalars, nested trees, raw values, duplicate keys, invalid transitions/UTF-8, parser depth boundaries and retained aliases, 1/4 workers',flush=True)
if __name__=='__main__':main()
