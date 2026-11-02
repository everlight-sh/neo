#!/usr/bin/env python3
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
def main():
    rng=random.Random(261102);atoms=[None,False,True,0,-1,-2**63,2**63-1,2**63,-2**63-1,1.0,1.25,1e300,'','\x00\n\t"\\é😀',[],{},[1,{'x':True}]];cases=[];expected=[]
    for _ in range(700):
        names=[rng.choice(['','key','x\x00é','\n"\\','😀'])+str(rng.randrange(8)) for _ in range(rng.randrange(20))];values=[rng.choice(atoms) for _ in names]
        cases.append(dict(keys=names,values=values));expected.append(dict(ok=True,value=dict(zip(names,values)),count=len(names)))
    for n in [0,1,2,8,65,512]:
        cases.extend([dict(keys=['x']*n,values=[]),dict(keys=[],values=[0]*n)]);expected.extend([dict(ok=True,value={},count=0)]*2 if n==0 else [dict(ok=False)]*2)
    for raw in ['ff','c080','eda080','f4908080','e282']:
        cases.extend([dict(keys=['x'],values=[0],keyBytes=[raw]),dict(keys=['x'],values=[],stringBytes=raw)])
        expected.extend([dict(ok=False)]*2)
    cases.append(dict(keys=['x'],values=[],missing=True));expected.append(dict(ok=False))
    for depth in range(125,132):
        for leaf in [False,True]:
            cases.append(dict(keys=['x'],values=[],depth=depth,leaf=leaf))
            if depth>(127 if leaf else 128):expected.append(dict(ok=False));continue
            v=7 if leaf else []
            for _ in range(depth if leaf else depth-1):v=[v]
            expected.append(dict(ok=True,value={'x':v},count=1))
    with tempfile.TemporaryDirectory(prefix='neo-object-encoder-') as tmp:
        binary=Path(tmp)/'object';build('tests/fixtures/json_object_encoder.neo',binary)
        for workers in [1,4]:
            for start in range(0,len(cases),40):
                batch=cases[start:start+40];data=b''.join(json.dumps(x,ensure_ascii=False).encode().hex().encode()+b'\n' for x in batch)
                run=subprocess.run(RUNNER+[str(binary)],input=data,capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
                assert run.returncode==0,(start,run.stderr)
                assert [json.loads(x) for x in run.stdout.splitlines()]==expected[start:start+40],start
    print(f'PASS {len(cases)} independent prepared-object encodings: exact integers, scalar/nested fragments, escaped Unicode/control keys and values, duplicate names and length mismatch, 1/4 workers',flush=True)
if __name__=='__main__':main()
