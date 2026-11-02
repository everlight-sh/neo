#!/usr/bin/env python3
import json,os,random,re,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build
class Object(list):pass
TOKEN=re.compile(r'\s+|"(?:\\.|[^"\\])*"|true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|[][{},:]')
def oracle(source):
 tokens=[];depth=0
 for match in TOKEN.finditer(source):
  raw=match[0]
  if raw.isspace() or raw in [',',':']:continue
  if raw in ['{','[']:kind=6 if raw=='{' else 5
  elif raw in ['}',']']:kind=-6 if raw=='}' else -5
  elif raw.startswith('"'):kind=7 if source[match.end():].lstrip().startswith(':') else 4
  elif raw=='null':kind=1
  elif raw in ['true','false']:kind=2
  else:kind=3
  tokens.append((kind,depth,raw,match.start()))
  depth+=1 if kind in [5,6] else -1 if kind in [-5,-6] else 0
 result=[]
 for i,(kind,depth,raw,start) in enumerate(tokens):
  skip=i+1
  if kind in [5,6]:
   level=1
   while level:
    level+=1 if tokens[skip][0] in [5,6] else -1 if tokens[skip][0] in [-5,-6] else 0;skip+=1
  integer=json.loads(raw) if kind==3 and re.fullmatch(r'-?\d+',raw) else None
  if integer is not None and not -2**63<=integer<2**63:integer=None
  view,count=0,0
  if 1<=kind<=6:
   value,_=json.JSONDecoder(object_pairs_hook=Object).raw_decode(source,start);view=kind;count=len(value) if kind in [5,6] else 0
  result.append(dict(kind=kind,depth=depth,raw=raw,text=json.loads(raw) if kind in [4,7] else None,integer=integer,skipKind=tokens[skip][0] if skip<len(tokens) else 0,viewKind=view,viewCount=count))
 return result

def main():
 rng=random.Random(261112);atoms=[None,False,True,0,-2**63,2**63-1,2**63,-2**63-1,1.0,1.25,1e300,'','\x00"\\é😀']
 def tree(d):
  if not d or rng.randrange(3)==0:return rng.choice(atoms)
  if rng.randrange(2):return [tree(d-1) for _ in range(rng.randrange(6))]
  return {rng.choice(['','a','é😀','\n"\\'])+str(i):tree(d-1) for i in range(rng.randrange(6))}
 cases=[json.dumps(v,ensure_ascii=False) for v in atoms+[[],{},[1,{},'x']]]+[json.dumps(tree(4),ensure_ascii=False) for _ in range(400)]
 cases+=[' { "a" : 1, "a" : [2,3], "\\u0061" : {"é":true} } ','[0,-0,1e0,-0.0,1E+3]']
 cases+=['['*depth+']'*depth for depth in [1,8,63,64,127,128,129]]
 invalid=['','[1,]','{"a":}','null false','"\\ud800"','['*130+']'*130]
 with tempfile.TemporaryDirectory(prefix='neo-json-tokens-') as temp:
  binary=Path(temp)/'tokens';build('tests/fixtures/json_tokens.neo',binary)
  for workers in [1,4]:
   for start in range(0,len(cases),20):
    batch=cases[start:start+20];payload=b''.join(x.encode().hex().encode()+b'\n' for x in batch);r=subprocess.run(RUNNER+[str(binary)],input=payload,capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90);assert r.returncode==0,(start,r.stderr)
    assert [json.loads(x) for x in r.stdout.splitlines()]==[oracle(x) for x in batch],start
   r=subprocess.run(RUNNER+[str(binary)],input=b''.join(x.encode().hex().encode()+b'\n' for x in invalid),capture_output=True,env={**os.environ,'NEO_THREADS':str(workers)},timeout=90);assert r.returncode==0,r.stderr
   assert [json.loads(x) for x in r.stdout.splitlines()]==[{'invalid':True}]*len(invalid)
 print(f'PASS {len(cases)} independent complete token streams and {len(invalid)} rejected sources: depths, scalar inspection, member names, skip/take spans, duplicate/escaped keys and retained cursor aliases, 1/4 workers',flush=True)
if __name__=='__main__':main()
