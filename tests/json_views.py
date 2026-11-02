#!/usr/bin/env python3
"""Independent cursor traversal, retained ownership and JSON materialization."""
import json,os,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
class Object(list):pass
def expected(value):
    kind=6 if isinstance(value,Object) else 5 if isinstance(value,list) else 1 if value is None else 2 if isinstance(value,bool) else 3 if isinstance(value,(int,float)) else 4
    def ordinary(v):
        if isinstance(v,Object):return {k:ordinary(x) for k,x in v}
        if isinstance(v,list):return [ordinary(x) for x in v]
        return v
    integer=value if kind==3 and isinstance(value,int) and -2**63<=value<2**63 else None
    return dict(kind=kind,value=ordinary(value),integer=integer,text=value if kind==4 else None,members=[[k,expected(x)] for k,x in value] if kind==6 else [],elements=[expected(x) for x in value] if kind==5 else [])
def main():
    rng=random.Random(261104);atoms=[None,False,True,0,-1,-2**63,2**63-1,2**63,-2**63-1,1.25,1e300,'','\x00\n"\\é😀']
    def tree(depth):
        if not depth or rng.randrange(3)==0:return rng.choice(atoms)
        if rng.randrange(2):return [tree(depth-1) for _ in range(rng.randrange(6))]
        return {rng.choice(['','key','\n"\\é😀'])+str(i):tree(depth-1) for i in range(rng.randrange(6))}
    cases=[json.dumps(x,ensure_ascii=False) for x in atoms+[[],{},[1,[],{},'x']]]
    cases += [json.dumps(tree(4),ensure_ascii=False) for _ in range(550)]
    cases += [' { "a" : 1, "a":2,"\\u0061":3 } ','{"a":[true, false,null],"empty":{}}','[ 0, -0, -0.0, 1e0 ]']
    invalid=['','{','[1,]','{"a":}','null x','[true false]','"\\ud800"']
    with tempfile.TemporaryDirectory(prefix='neo-json-views-') as temp:
        binary=Path(temp)/'views';build('tests/fixtures/json_views.neo',binary)
        for workers in [1,4]:
            for start in range(0,len(cases),30):
                batch=cases[start:start+30];data=b''.join(x.encode().hex().encode()+b'\n' for x in batch)
                result=subprocess.run(RUNNER+[str(binary)],input=data,capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
                assert result.returncode==0,result.stderr
                actual=[json.loads(x) for x in result.stdout.splitlines()]
                wanted=[expected(json.loads(x,object_pairs_hook=Object)) for x in batch]
                assert actual==wanted,(start,next(((a,b) for a,b in zip(actual,wanted) if a!=b),None))
            result=subprocess.run(RUNNER+[str(binary)],input=b''.join(x.encode().hex().encode()+b'\n' for x in invalid),capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90)
            assert result.returncode==0,result.stderr
            assert [json.loads(x) for x in result.stdout.splitlines()]==[{'invalid':True}]*len(invalid)
    print(f'PASS {len(cases)} independent full cursor trees and {len(invalid)} invalid inputs: duplicates, escaped keys, integer limits, nested materialization, repeated/end cursors and retained aliases, 1/4 workers',flush=True)
if __name__=='__main__':main()
