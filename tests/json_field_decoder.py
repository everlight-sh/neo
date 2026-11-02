#!/usr/bin/env python3
"""Prepared field decoding versus json_parse/json_get on valid and invalid inputs."""
import json
import random
import subprocess
import usability_smoke as smoke

VALUES=[None,True,False,0,-1,7,9223372036854775807,-9223372036854775808,'','café 🚀','"\\\n\t\x00','plain text',
        1.5,-0.0,1e300,[],[1,2,3],[{'id':1}],{'inner':{'a':[1,'x']}},{}]
NAMES=['id','name','values','target','','café 🚀','ta"rget','x'*20,'missing']

def obj(rng):
    row={f'pad{j}':rng.choice(VALUES) for j in range(rng.choice([0,1,3,6]))}
    for name in rng.sample(NAMES,rng.randrange(len(NAMES))):row[name]=rng.choice(VALUES)
    return row

def text_of(value,rng):
    text=json.dumps(value,ensure_ascii=rng.random()<.5,separators=rng.choice([(',',':'),(', ',': ')]))
    if rng.random()<.2:text=text.replace('"target":','"ta\\u0072get":')
    if rng.random()<.2 and text.endswith('}') and len(text)>2:text=text[:-1]+',"id":'+json.dumps(rng.choice(VALUES))+'}'
    return (rng.choice(['',' ','\n\t '])+text+rng.choice(['',' ','\r\n'])).encode()

def mutate(data,rng):
    choice=rng.randrange(8)
    if choice==0 and len(data)>1:return data[:rng.randrange(1,len(data))]
    if choice==1:return data.replace(b'}',b',}',1)
    if choice==2:return data.replace(b']',b',]',1)
    if choice==3:return data+b'x'
    if choice==4:return data.replace(b'"',b'"\xc0\x80',1)
    if choice==5:return data.replace(b':',b'',1)
    if choice==6:return data.replace(b'0',b'01',1)
    return b'{}{}' if rng.random()<.5 else b'[,{}]'

def main():
    binary=smoke.build('json-field-decoder','tests/fixtures/json_field_decoder.neo')
    rng=random.Random(20261030);cases=[]
    for i in range(1200):
        names=rng.sample(NAMES,rng.randrange(1,len(NAMES)+1))
        if i%2:mode='object';data=text_of(obj(rng),rng)
        else:
            rows=[obj(rng) for _ in range(rng.choice([0,1,2,5,20]))]
            if rng.random()<.1 and rows:rows[rng.randrange(len(rows))]=rng.choice([1,'x',[],None])
            mode='array';data=text_of(rows,rng)
        if i%4==3:data=mutate(data,rng)
        cases.append({'mode':mode,'names':names,'text':data.hex()})
    nested=b'{"id":'+b'['*130+b']'*130+b'}'
    for data,mode in [(b'{}','object'),(b'[]','array'),(b'[{}]','array'),(b'{"id":1,"id":2}','object'),(b'{"\\u0069d":3}','object'),
                      (b'[{"id":1},{"id":2}]   ','array'),(b'[{"id":1}] x','array'),(b'{"id":1} {','object'),(nested,'object'),(b'[[]]','array'),(b'','object'),(b'  ','array')]:
        cases.append({'mode':mode,'names':['id','name'],'text':data.hex()})
    lines=b''.join(json.dumps(case).encode().hex().encode()+b'\n' for case in cases)
    result=subprocess.run(smoke.RUNNER+[str(binary)],input=lines,capture_output=True,timeout=120)
    assert result.returncode==0,result.stderr[-2000:]
    replies=result.stdout.decode().split()
    assert len(replies)==len(cases),(len(replies),len(cases))
    failed=[case for case,reply in zip(cases,replies) if reply!='1']
    assert not failed,(len(failed),failed[:3])
    print(f'PASS {len(cases)} prepared field decodes match json_parse/json_get: objects and arrays of objects, escaped/duplicate/Unicode keys, nested and non-object values, integer limits and invalid inputs',flush=True)

if __name__=='__main__':main()
