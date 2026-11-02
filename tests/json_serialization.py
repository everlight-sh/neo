#!/usr/bin/env python3
"""Independent constructor/update/escaping/alias/depth differential corpus."""
import json,os,random,shlex,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'.kernel-build/json-serialization';folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'probe'
    command=[sys.executable,'-m','neoc','build','tests/fixtures/json_construct_probe.neo','--library-cache',str(folder/'libraries'),'--library-root',str(ROOT/'stdlib'),'--library-root',str(ROOT/'runtime'),'-o',str(binary)]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (folder/'build.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,(result.stdout[-3000:],result.stderr[-3000:])
    assert not subprocess.check_output(['nm','-u',str(binary)],text=True).strip()
    rng=random.Random(602623)
    atoms=[None,True,False,0,-1,2**63-1,-2**63,2**63,-2**63-1,1.0,1.5,1e300,'','café 🚀','\x00\n\t"\\',[],{},[1,{'nested':['x',None]}],{'a':1,'b':[1,2]}]
    corpus=[]
    for i in range(400):
        keys=[rng.choice(['a','escaped"\\key','café 🚀','x\x00y','',str(j)]) for j in range(rng.randrange(0,20))]
        values=[rng.choice(atoms) for _ in keys]
        text=''.join(chr(j) for j in range(32))+' café 🚀 '+('\\"'*(i%9)) if i%3 else ''.join(rng.choice(' a\\"\n\télève') for _ in range(rng.randrange(0,300)))
        corpus.append({'keys':keys,'values':values,'key':rng.choice(keys) if keys and i%2 else 'new-key','replacement':rng.choice(atoms),'text':text,'nested':'[]'})
    for depth in range(125,132):
        for leaf in ['', '0','"leaf"','{}']:
            corpus.append({'keys':[],'values':[],'key':'depth','replacement':True,'text':'','nested':'['*depth+leaf+']'*depth})
    runner=shlex.split(os.environ.get('NEO_RUNNER',''))
    for start in range(0,len(corpus),50):
        batch=corpus[start:start+50]
        data=''.join(json.dumps(row,ensure_ascii=False).encode().hex()+'\n' for row in batch).encode()
        result=subprocess.run(runner+[str(binary)],input=data,capture_output=True,env={**os.environ,'NEO_THREADS':'1'},timeout=60)
        assert result.returncode==0,result.stderr
        replies=[json.loads(line) for line in result.stdout.splitlines()];assert len(replies)==len(batch),(start,result.stdout[-1000:])
        for row,reply in zip(batch,replies):
            expected=dict(zip(row['keys'],row['values']));updated={**expected,row['key']:row['replacement']}
            assert reply['object']==expected and reply['array']==row['values'],(row,reply)
            assert reply['updated']==updated and reply['got']==row['replacement'] and reply['quoted']==row['text'],(row,reply)
            assert reply['keys']==row['keys']+([] if row['key'] in row['keys'] else [row['key']]),(row,reply)
            assert reply['alias'] and reply['missingRejected'],(row,reply)
            assert reply['indexed']==row['values'] and reply['indexedKeys']==row['keys'],(row,reply)
            value=row['replacement'];kind=1 if value is None else 2 if isinstance(value,bool) else 3 if isinstance(value,(int,float)) else 4 if isinstance(value,str) else 5 if isinstance(value,list) else 6
            integer=isinstance(value,int) and not isinstance(value,bool) and -(1<<63)<=value<(1<<63)
            assert (reply['atomKind'],reply['atomInteger'],reply['atomValue'])==(kind,integer,value if integer else 0),(row,reply)
            assert reply['wrapped']==(reply['nested'] and reply['parsedWrapper']),(row,reply)
    print(f'PASS {len(corpus)} JSON serialization/update/escaping/alias/depth differential cases',flush=True)

if __name__=='__main__':main()
