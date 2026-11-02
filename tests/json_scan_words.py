#!/usr/bin/env python3
"""Every byte at word/tail boundaries, UTF-8, escapes and array scan counts."""
import json,os,subprocess
from pathlib import Path
from agent_codecs import RUNNER,build
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'.kernel-build/json-scan-words';folder.mkdir(parents=True,exist_ok=True)
    binary=folder/'probe';build('tests/fixtures/json_scan_words.neo',binary)
    cases=[]
    for prefix in range(24):
        for byte in range(256):cases.append(b'["'+b'a'*prefix+bytes([byte])+b'b'*19+b'",0]')
        for text in ['café😀','é'*20,'\\\"\t\n\x00','x'*1000,'']:
            for ascii in [False,True]:cases.append(json.dumps(['a'*prefix+text,{'k':text},None],ensure_ascii=ascii).encode())
        for invalid in [b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xe2\x82',b'\\uD800',b'\\q',b'\\u12XZ']:
            cases.append(b'"'+b'a'*prefix+invalid+b'"')
    cases.extend([b'[]',b'[ ]',b'[0]',b'[0,]',b'[',b'[true false]',b'[1e,0]',b'[{},[],[1,2],"a"]',b'[[1],2]junk',b'{}',b'0',b'null'])
    for n in range(40):cases.extend([json.dumps(list(range(n))).encode(),json.dumps({'x'*n:'y'*n}).encode()])
    for start in range(0,len(cases),80):
        batch=cases[start:start+80]
        result=subprocess.run(RUNNER+[str(binary)],input=b''.join(x.hex().encode()+b'\n' for x in batch),capture_output=True,env={**os.environ,'NEO_THREADS':'1'},timeout=60)
        assert result.returncode==0,result.stderr
        replies=[json.loads(line) for line in result.stdout.splitlines()];assert len(replies)==len(batch)
        for raw,reply in zip(batch,replies):
            try:
                value=json.loads(raw.decode('utf-8'))
                # Python accepts unpaired escaped surrogates; Neo requires Unicode scalar values.
                json.dumps(value,ensure_ascii=False).encode('utf-8')
            except (ValueError,UnicodeError):assert reply=={'ok':False},(raw,reply);continue
            assert reply=={'ok':True,'count':len(value) if isinstance(value,list) else 0,'value':value},(raw,reply,value)
    print(f'PASS {len(cases)} independent JSON word/tail/UTF-8/escape/array-count cases',flush=True)
if __name__=='__main__':main()
