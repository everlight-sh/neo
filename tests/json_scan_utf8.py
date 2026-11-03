#!/usr/bin/env python3
"""UTF-8 sequences and integers at every word and end-of-source offset, against
Python's strict decoder: json_parse on objects and arrays, and the prepared field
decoder against json_parse/json_get on the same objects."""
import json,os,subprocess
from pathlib import Path
from agent_codecs import RUNNER,build
ROOT=Path(__file__).resolve().parents[1]
VALID=['é','ß','\u0080','߿','ࠀ','￿','€','中文','\U00010000','\U0010ffff','😀','café 🚀','aé😀中']
INVALID=[b'\xc0\x80',b'\xc1\xbf',b'\xe0\x80\x80',b'\xe0\x9f\xbf',b'\xed\xa0\x80',b'\xed\xbf\xbf',b'\xf0\x80\x80\x80',b'\xf0\x8f\xbf\xbf',
         b'\xf4\x90\x80\x80',b'\xf5\x80\x80\x80',b'\xff',b'\x80',b'\xbf\xbf',b'\xc3',b'\xe2\x82',b'\xf0\x9f\x98',b'\xc3\x28',b'\xe2\x28\xa1',b'\xf0\x28\x8c\xbc']
NUMBERS=['0','-0','01','-01','1','12','123','999','-7','00','1.5','1e5','1E+5','-1.25e-3','-','-a','1.','1e','1e+','0.0',
         *[str(10**k+k) for k in range(20)],*['-'+'9'*k for k in range(1,20)],'9223372036854775807','-9223372036854775808','9223372036854775808']

def expected(raw):
    try:
        value=json.loads(raw.decode('utf-8'))
        json.dumps(value,ensure_ascii=False).encode('utf-8')
        return value
    except (ValueError,UnicodeError):return None

def documents():
    out=[]
    texts=[t.encode() for t in VALID]+INVALID
    for prefix in range(0,13):
        pad=b'a'*prefix
        for text in texts:
            for tail in range(0,10,3):
                space=b' '*tail
                out+=[b'{"k":"'+pad+text+b'"'+space+b'}',b'{"'+pad+text+b'":1'+space+b'}',b'{"a":["'+pad+text+b'"'+space+b'],"k":0}',
                      b'["'+pad+text+b'",1'+space+b']',b'{"k":"'+pad+text+b'x'*9+b'","n":2}']
    for number in NUMBERS:
        for tail in range(0,10):
            space=b' '*tail;n=number.encode()
            out+=[b'{"n":'+n+space+b'}',b'{"n":'+n+space+b',"k":"x"}',b'['+n+space+b']',b'{"a":['+n+b','+n+space+b'],"n":'+n+b'}']
    return out

def run(binary,lines):
    result=subprocess.run(RUNNER+[str(binary)],input=b''.join(lines),capture_output=True,env={**os.environ,'NEO_THREADS':'1'},timeout=600)
    assert result.returncode==0,result.stderr[-2000:]
    return result.stdout.splitlines()

def main():
    folder=ROOT/'.kernel-build/json-scan-utf8';folder.mkdir(parents=True,exist_ok=True)
    parse=folder/'parse';build('tests/fixtures/json_scan_words.neo',parse)
    fields=folder/'fields';build('tests/fixtures/json_field_decoder.neo',fields)
    cases=documents()
    replies=run(parse,[x.hex().encode()+b'\n' for x in cases]);assert len(replies)==len(cases)
    accepted=0
    for raw,line in zip(cases,replies):
        value=expected(raw);reply=json.loads(line)
        if value is None:assert reply=={'ok':False},(raw,reply);continue
        accepted+=1
        assert reply=={'ok':True,'count':len(value) if isinstance(value,list) else 0,'value':value},(raw,reply,value)
    names=['k','n','a','x']+[t+'x' for t in VALID[:4]]
    objects=[raw for raw in cases if raw.startswith(b'{')]
    lines=[json.dumps({'mode':'object','names':names+[name] if (name:=key_name(raw)) not in names+[None] else names,'text':raw.hex()}).encode().hex().encode()+b'\n' for raw in objects]
    lines+=[json.dumps({'mode':'array','names':names,'text':(b'['+raw+b','+raw+b']').hex()}).encode().hex().encode()+b'\n' for raw in objects[::7]]
    replies=run(fields,lines);assert len(replies)==len(lines)
    failed=[(line,reply) for line,reply in zip(lines,replies) if reply!=b'1']
    shown=[(case['mode'],case['names'],bytes.fromhex(case['text'])) for case in (json.loads(bytes.fromhex(line[:-1].decode())) for line,_ in failed[:5])]
    assert not failed,(len(failed),shown)
    print(f'PASS {len(cases)} UTF-8/integer word and end-of-source cases ({accepted} valid) and {len(lines)} prepared decodes',flush=True)

def key_name(raw):
    """The first key of a valid object, so the decoder also matches non-ASCII keys."""
    value=expected(raw)
    return next(iter(value)) if isinstance(value,dict) and value else None

if __name__=='__main__':main()
