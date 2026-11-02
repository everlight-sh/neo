#!/usr/bin/env python3
"""JSON key comparison against independent binary and decoded-key models."""
import json,random,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
    rng=random.Random(251025);cases=0
    with tempfile.TemporaryDirectory(prefix='neo-json-key-words-') as tmp:
        binary=Path(tmp)/'keys';build('tests/fixtures/json_key_words.neo',binary)
        def run(mode,name,document,offset=0):
            nonlocal cases
            p=subprocess.run(RUNNER+[str(binary),str(mode),str(len(name)),str(offset)],input=name+document,capture_output=True,timeout=10)
            assert p.returncode==0,(mode,name,document,p.stderr);cases+=1;return p.stdout
        for size in [*range(18),31,32,33,63,64,65,127,256]:
            for byte in range(256):
                raw=bytearray(b'x'*size)
                if size:raw[byte%size]=byte
                raw=bytes(raw);offset=byte%16;document=b'p'*offset+b'"'+raw+b'"'
                expected=b'equal' if b'\\' not in raw else b'different'
                assert run(1,raw,document,offset)==expected,(raw,offset)
                if size:
                    changed=bytearray(raw);changed[-1]^=1
                    assert run(1,bytes(changed),document,offset)==b'different'
        keys=['','id','name','values','\\','"','\n','\0','\\n','\\u0061','café 🚀','🚀'*8]
        keys += ['k'*n+'é\\"\0' for n in [1,2,3,4,7,8,9,15,16,17,31,32,33,127,256]]
        for key in keys:
            for ascii_only in [False,True]:
                encoded=json.dumps(key,ensure_ascii=ascii_only).encode()
                document=b'{'+encoded+b':1,"other":-9,'+encoded+b':123}'
                assert run(0,key.encode(),document)==b'123',(key,document)
                assert run(0,(key+'!').encode(),document)==b'missing'
        for document in [b'{"\\u0061":123}',b'{"\\n":123}',b'{"\\u0000":123}',b'{"\\ud83d\\ude80":123}']:
            actual=next(iter(json.loads(document)))
            assert run(0,actual.encode(),document)==b'123'
            spelling=document[2:document.index(b'":')]
            assert run(0,spelling,document)==b'missing',(document,spelling)
    print(f'PASS JSON key words: {cases} binary/tail/alignment/Unicode/escaped/duplicate/missing-key cases',flush=True)
if __name__=='__main__':main()
