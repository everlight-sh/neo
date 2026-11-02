#!/usr/bin/env python3
import datetime, json, math, os, random, shlex, stat, subprocess, tempfile, unicodedata
from pathlib import Path
from agent_codecs import ROOT,RUNNER,build

def main():
    rng=random.Random(781)
    with tempfile.TemporaryDirectory(prefix='neo-utilities-') as tmp:
        binary=Path(tmp)/'utilities';build('tests/fixtures/agent_utilities.neo',binary)
        def run(mode,data,extra=()):
            p=subprocess.run(RUNNER+[str(binary),str(mode),*map(str,extra)],input=data,capture_output=True,timeout=20)
            assert p.returncode==0,(mode,data[:80],p.returncode,p.stderr)
            return p.stdout
        utc=datetime.timezone.utc
        values=[-62135596800000,-1,0,1,253402300799999,951782400000]+[rng.randrange(-62135596800000,253402300800000) for _ in range(100)]
        for ms in values:
            expected=datetime.datetime(1970,1,1,tzinfo=utc)+datetime.timedelta(milliseconds=ms)
            text=expected.isoformat(timespec='milliseconds').replace('+00:00','Z')
            assert run(1,str(ms).encode()).decode()==text,(ms,text)
            assert run(0,text.encode())==str(ms).encode(),text
        for text in ['2024-02-29T13:42:09.123456+02:30','2023-01-02T03:04:05-06:00']:
            date=datetime.datetime.fromisoformat(text);ms=int((date-datetime.datetime(1970,1,1,tzinfo=utc)).total_seconds()*1000)
            assert run(0,text.encode())==str(ms).encode(),text
        for text in ['2023-02-29T00:00:00Z','2024-01-01T24:00:00Z','0000-01-01T00:00:00Z','2024-01-01T00:00:00.Z','2024-01-01T00:00:00+24:00','2024-01-01T00:00:60Z']:
            assert run(0,text.encode())==b'error',text
        print('PASS RFC3339 against datetime: years 1..9999, negative epochs, leap days, fractions, offsets and invalid dates',flush=True)
        samples=['Straße Σίσυφος İ CAFÉ ﬃ ẞ 𐐀','\u2003 one\u00a0two\t三\n四',''.join(c for _ in range(1000) if unicodedata.category(c:=chr(rng.randrange(0xd800)))!='Cn')]
        for text in samples:
            assert run(2,text.encode())==text.casefold().encode(),text[:40]
            assert run(3,text.encode())==''.join(v+'\n' for v in text.split()).encode(),text[:40]
        for code in [0,65,0x301,0x4e00,0x1f680,0x10400,0x10ffff]+[rng.randrange(0x110000) for _ in range(100)]:
            if unicodedata.unidata_version!='16.0.0' and unicodedata.category(chr(code))=='Cn':continue
            assert run(7,str(code).encode())==(b'true' if unicodedata.category(chr(code))[0] in 'LN' else b'false'),code
        for data in [b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\xff',b'\xe2\x82']:
            assert run(2,data)==b'error',data
        print('PASS Unicode 16 case folding, scalar iteration, word categories, whitespace splitting and malformed UTF-8',flush=True)
        for mode,oracle,values in [(4,math.log1p,[-.999999,-.5,-1e-10,0,1e-20,.1,1,10,1e10]),(5,math.exp,[-740,-700,-10,-.1,0,.1,10,100,700])]:
            for value in values:
                got=float(run(mode,repr(value).encode()));expected=oracle(value)
                assert math.isclose(got,expected,rel_tol=2e-12,abs_tol=5e-324),(mode,value,got,expected)
        print('PASS finite log1p/exp numerical oracle (2e-12 relative tolerance; not correctly-rounded libm)',flush=True)
        destination=Path(tmp)/'state.json'
        for payload in [b'',b'first',rng.randbytes(65536)]:
            assert run(6,payload,[destination])==b'stored'
            assert destination.read_bytes()==payload
            assert stat.S_IMODE(destination.stat().st_mode)==0o600
            assert not list(Path(tmp).glob('state.json.tmp.*'))
        print('PASS exclusive private atomic replacement, complete contents and temporary cleanup',flush=True)
if __name__=='__main__':main()
