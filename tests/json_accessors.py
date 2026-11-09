#!/usr/bin/env python3
"""JSON accessors, Unicode boundaries, indexing growth and ownership differentials."""
import json
import random
import subprocess
import usability_smoke as smoke


def main():
    binary=smoke.build('json-access-probe','tests/fixtures/json_access_probe.neo')
    values=[None,True,False,0,-1,9223372036854775807,-9223372036854775808,'',
        'café 🚀','"\\\n\t\x00','\u007f\u0080\u07ff\u0800\ud7ff\ue000\uffff\U00010000\U0010ffff',
        [],[1,2,3],[{},[],None,'café 🚀'],{'inner':{'a':[1,'x']}},{'inner':[]},{}]
    corpus=[]
    rng=random.Random(24102417)
    for i in range(700):
        row={f'padding-{j}':rng.choice(values) for j in range(rng.choice([0,1,3,4,5,8,17,65]))}
        if i%7:row['target']=rng.choice(values)
        text=json.dumps(row,ensure_ascii=i%2==0,separators=(',',':'))
        if i%3==0:text=text.replace('"target":','"ta\\u0072get":')
        if i%5==0 and 'target' in row:text=text[:-1]+',"target":'+json.dumps(rng.choice(values),ensure_ascii=True)+'}'
        corpus.append((' \n\t'+text+' \r\n').encode())
    corpus += [b'{"target":"old","ta\\u0072get":"last"}',b'{"target":1,"ta\\u0072get":2,"target":3}',
        b'{"target":{"inner":1,"inner":2}}',b'{"target":[{"inner":1},[2,3],null]}']
    # Exercise long plain runs separated by escapes, dense escapes, surrogate
    # pairs and control bytes with both literal UTF-8 and ASCII JSON encodings.
    for text in ['plain'*4000+'"tail', '\\"\n\t\x00'*2000, 'café 🚀'*2000, 'prefix'+''.join(chr(i) for i in range(32))+'\U0010ffff']:
        for ascii_only in (True,False):corpus.append(json.dumps({'target':text},ensure_ascii=ascii_only).encode())
    for data in (b'\xc0\x80',b'\xc1\xbf',b'\xe0\x80\x80',b'\xed\xa0\x80',b'\xf0\x80\x80\x80',b'\xf4\x90\x80\x80',b'\xf5\x80\x80\x80',b'\x80',b'\xc2',b'\xe1\x80',b'\xf1\x80\x80'):
        corpus.extend([b'{"target":"'+data+b'"}',b'{"'+data+b'":0}',b'["'+data+b'"]'])
    # Batch stdin/output keeps the probe bounded and avoids quadratic test-harness copying.
    for start in range(0,len(corpus),100):
        cases=corpus[start:start+100]
        result=subprocess.run(smoke.RUNNER+[str(binary)],input=b''.join(x.hex().encode()+b'\n' for x in cases),capture_output=True,timeout=90)
        assert result.returncode==0,result.stderr
        replies=[json.loads(x) for x in result.stdout.splitlines()];assert len(replies)==len(cases)
        for case,reply in zip(cases,replies):
            try:row=json.loads(case.decode('utf-8'))
            except (ValueError,UnicodeError):assert reply=={'ok':False},(case,reply);continue
            value=row.get('target');items=value if isinstance(value,list) else []
            expected={'ok':True,'present':'target' in row,'value':value,
                'text':value if isinstance(value,str) else None,'count':len(items),'items':items,
                'second':items[1] if len(items)>1 else None,'inner':value.get('inner') if isinstance(value,dict) else None}
            assert reply==expected,(case,reply,expected)
    print(f'PASS JSON accessor differential: {len(corpus)} Unicode/escaped-key/duplicate/nested/wide-object/ownership cases',flush=True)


if __name__=='__main__':main()
