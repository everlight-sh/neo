#!/usr/bin/env python3
"""std:deflate inflate (raw DEFLATE, zlib, gzip, HTTP Content-Encoding) checked
differentially against Python's zlib and gzip modules.

zlib is a test oracle and stream generator only; the Neo executable links no
compression library. Raw/zlib/gzip outputs must match the oracle byte for byte,
and the oracle's rejections must be rejections here too (never a trap).
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import struct
import subprocess
import sys
import tempfile
import time
import zlib

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))

PROGRAM=r'''import "std:deflate"
import "std:io"
import "std:time"
fn decode(kind:i64,bytes:Arr u8 n,limit:i64) -> BytesResult
  = if kind==0 then inflate_raw(bytes,limit) else if kind==1 then zlib_decode(bytes,limit) else if kind==2 then gzip_decode(bytes,limit)
    else if kind==3 then let split=str_find(bytes,"\n") in
      if !split.present then bytes_error(22,"missing encoding line",0) else
      http_content_decode(str_slice(bytes,0,split.value),str_slice(bytes,split.value+1,n),limit)
    else if kind==4 then bytes_ok(concat(int_text(crc32(bytes))," ",int_text(adler32(bytes)),"\n"))
    else bytes_error(22,"unknown mode",0)
fn le32(value:i64) -> Arr u8 _ = byte_write_le(arr(i in 0..4) u8(0),0,value,4)
fn record(result:BytesResult) -> Arr u8 _
  = if result.ok then concat("\x01",le32(len(result.value)),result.value)
    else concat("\x00",le32(result.error.code),le32(result.error.position))
; Batch: [u32 length][bytes]... -> [u8 ok][u32 length|code][payload|u32 position]...
fn batch(kind:i64,bytes:Arr u8 n,limit:i64) -> Arr u8 _
  = loop(at=0,out="") while at>=0 && at+4<=n
      next(at+4+bytes_le32(bytes,at),
        let size=bytes_le32(bytes,at) in concat(out,record(decode(kind,str_slice(bytes,at+4,at+4+size),limit)))) yield out
effect(fs,time,process) fn main(mode:i64,limit:i64,reps:i64) -> unit
  = let input=file_read(0,67108864) in check input.ok in let bytes=input.value in
    if mode>=20 then let written=print_out(batch(mode-20,bytes,limit)) in noop() else
    if mode>=10 then
      let start=monotonic_ns() in
      let total=loop(i=0,total=0) while i<reps next(i+1,let r=decode(mode-10,bytes,limit) in total+(if r.ok then len(r.value) else -1)) yield total in
      let stop=monotonic_ns() in
      let written=print_out(concat(int_text(stop.value-start.value)," ",int_text(total),"\n")) in noop() else
    let result=decode(mode,bytes,limit) in
    if result.ok then let written=print_out(result.value) in noop() else
      let written=print_out(concat(int_text(result.error.code)," ",int_text(result.error.position)," ",result.error.message)) in process_exit(2)
'''

RAW,ZLIB,GZIP,HTTP,SUMS=0,1,2,3,4
LIMIT=1<<40


# ---- Oracles ---------------------------------------------------------------

def oracle(data,wbits):
    """zlib's verdict for one complete stream: output bytes, or None when rejected
    (malformed, truncated, or followed by trailing bytes)."""
    d=zlib.decompressobj(wbits)
    try:out=d.decompress(data)+d.flush()
    except zlib.error:return None
    return out if d.eof and not d.unused_data else None

def gzip_oracle(data):
    try:return gzip.decompress(data)
    except (OSError,EOFError,zlib.error):return None

def compress(data,level=-1,wbits=15,mem=8,strategy=zlib.Z_DEFAULT_STRATEGY,zdict=None):
    c=zlib.compressobj(level,zlib.DEFLATED,wbits,mem,strategy,**({'zdict':zdict} if zdict else {}))
    return c.compress(data)+c.flush()


# ---- Hand-built fixed-Huffman streams (distances/lengths zlib never emits) --

class Bits:
    def __init__(self):self.value=0;self.count=0;self.out=bytearray()
    def put(self,value,count):
        self.value|=value<<self.count;self.count+=count
        while self.count>=8:self.out.append(self.value&255);self.value>>=8;self.count-=8
    def code(self,code,length):self.put(int(format(code,f'0{length}b')[::-1],2),length)
    def bytes(self):
        if self.count:self.out.append(self.value&255);self.value=0;self.count=0
        return bytes(self.out)

LEN_BASE=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
LEN_EXTRA=[0]*8+[1]*4+[2]*4+[3]*4+[4]*4+[5]*4+[0]
DIST_BASE=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
DIST_EXTRA=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]

def fixed_symbol(w,sym):
    if sym<144:w.code(0x30+sym,8)
    elif sym<256:w.code(0x190+sym-144,9)
    elif sym<280:w.code(sym-256,7)
    else:w.code(0xc0+sym-280,8)

def fixed_stream(*blocks):
    """One fixed-Huffman block per ops list, the last one final. ops: ints are
    literals, (length, distance) are matches, ('sym', s) raw literal/length
    symbols, ('dist', length_symbol, dcode) raw distance codes, ('len284', d)
    encodes length 258 as symbol 284 plus 31 extra."""
    w=Bits()
    for index,ops in enumerate(blocks):
        w.put(1 if index==len(blocks)-1 else 0,1);w.put(1,2);fixed_ops(w,ops);fixed_symbol(w,256)
    return w.bytes()

def fixed_ops(w,ops):
    for op in ops:
        if isinstance(op,int):fixed_symbol(w,op)
        elif op[0]=='sym':fixed_symbol(w,op[1])
        elif op[0]=='dist':fixed_symbol(w,op[1]);w.code(op[2],5)
        elif op[0]=='len284':
            fixed_symbol(w,284);w.put(31,5);d=op[1]
            j=max(j for j in range(30) if DIST_BASE[j]<=d);w.code(j,5);w.put(d-DIST_BASE[j],DIST_EXTRA[j])
        else:
            length,d=op;i=max(i for i in range(29) if LEN_BASE[i]<=length)
            fixed_symbol(w,257+i);w.put(length-LEN_BASE[i],LEN_EXTRA[i])
            j=max(j for j in range(30) if DIST_BASE[j]<=d);w.code(j,5);w.put(d-DIST_BASE[j],DIST_EXTRA[j])

def zlib_header(cmf,flags=0):
    return bytes([cmf,flags+(31-(cmf*256+flags)%31)%31])

def zlib_wrap(raw,data):
    return b'\x78\x9c'+raw+struct.pack('>I',zlib.adler32(data))

def gzip_member(data,raw=None,flags=0,name=b'',comment=b'',extra=b'',mtime=0,header_crc=None):
    raw=compress(data,6,-15) if raw is None else raw
    header=b'\x1f\x8b\x08'+bytes([flags])+struct.pack('<I',mtime)+b'\x00\xff'
    if flags&4:header+=struct.pack('<H',len(extra))+extra
    if flags&8:header+=name+b'\x00'
    if flags&16:header+=comment+b'\x00'
    if flags&2:header+=struct.pack('<H',zlib.crc32(header)&0xffff if header_crc is None else header_crc)
    return header+raw+struct.pack('<II',zlib.crc32(data),len(data)&0xffffffff)


# ---- Corpora ---------------------------------------------------------------

def text_corpus(rng,size):
    words=[''.join(rng.choice('etaoinshrdlucmfwypvbgkjqxz') for _ in range(rng.randint(1,9))) for _ in range(800)]
    parts=[];total=0
    while total<size:
        line=' '.join(rng.choice(words) for _ in range(rng.randint(3,14)))
        line=line.capitalize()+rng.choice(['.','.','?','!',';',','])+('\n' if rng.random()<0.3 else ' ')
        parts.append(line);total+=len(line)
    return ''.join(parts).encode()[:size]

def source_corpus():
    files=sorted((ROOT/'stdlib').glob('*.neo'))+sorted((ROOT/'neoc').glob('*.py'))
    return b''.join(path.read_bytes() for path in files)


def main():
    rng=random.Random(19511952)
    with tempfile.TemporaryDirectory(prefix='neo-deflate-') as tmp:
        root=Path(tmp);source=root/'deflate_probe.neo';binary=root/'deflate_probe'
        source.write_text(PROGRAM)
        built=subprocess.run([sys.executable,'-m','neoc','build',str(source),'-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
        assert built.returncode==0,(built.stdout[-4000:],built.stderr[-4000:])
        report=json.loads(built.stdout);assert report['undefined_symbols']==[],report['undefined_symbols']
        counts={'cases':0}

        def run(mode,data,limit=LIMIT,reps=1):
            r=subprocess.run(RUNNER+[str(binary),str(mode),str(limit),str(reps)],input=data,capture_output=True,timeout=300)
            assert r.returncode in (0,2),(mode,r.returncode,r.stderr[-2000:])
            counts['cases']+=1
            if r.returncode==0:return True,r.stdout
            code,position,message=r.stdout.decode().split(' ',2)
            return False,(int(code),int(position),message)

        def batch(kind,cases,limit=LIMIT):
            payload=b''.join(struct.pack('<I',len(c))+c for c in cases)
            r=subprocess.run(RUNNER+[str(binary),str(20+kind),str(limit),'1'],input=payload,capture_output=True,timeout=600)
            assert r.returncode==0,(kind,r.returncode,r.stderr[-2000:])
            out=r.stdout;at=0;results=[]
            while at<len(out):
                ok=out[at];value=struct.unpack_from('<I',out,at+1)[0]
                if ok:results.append(out[at+5:at+5+value]);at+=5+value
                else:results.append(('error',value,struct.unpack_from('<I',out,at+5)[0]));at+=9
            assert len(results)==len(cases),(len(results),len(cases))
            counts['cases']+=len(cases)
            return results

        def agree(kind,cases,expected,label,limit=LIMIT):
            """Every case must decode to its expected bytes, or fail where expected is None."""
            for index,(case,want,got) in enumerate(zip(cases,expected,batch(kind,cases,limit))):
                if want is None:assert isinstance(got,tuple),(label,index,len(case),'accepted a stream zlib rejects')
                else:assert got==want,(label,index,len(case),got if isinstance(got,tuple) else (len(got),len(want)))

        def expect(mode,data,want,limit=LIMIT):
            ok,got=run(mode,data,limit);assert ok,(mode,got);assert got==want,(mode,len(got),len(want))

        def reject(mode,data,code=None,limit=LIMIT):
            ok,got=run(mode,data,limit);assert not ok,(mode,len(data),'accepted')
            if code is not None:assert got[0]==code,(mode,got)
            return got

        # Checksums against zlib.crc32 / zlib.adler32, around the 8-byte and 1 MiB strides.
        for size in [0,1,7,8,9,15,16,17,63,64,65,1000,65535,65536,1048575,1048576,1048577,3000001]:
            data=rng.randbytes(size) if size%2 else bytes([255])*size
            ok,got=run(SUMS,data);assert ok
            assert got==f'{zlib.crc32(data)} {zlib.adler32(data)}\n'.encode(),(size,got)
        print('PASS crc32/adler32 match zlib for 18 sizes 0..3 MB including 0xFF runs (Adler reduction stress)',flush=True)

        corpora={
            'empty':b'','one':b'Z','random':rng.randbytes(150_000),'text':text_corpus(rng,250_000),
            'source':source_corpus()[:400_000],
            'repetitive':b'a'*70_000+b'ab'*20_000+bytes(range(256))*120+b'abcdefg'*9000+b'\x00'*40_000,
            'periods':b''.join(rng.randbytes(p)*(1500//p+1) for p in range(1,40)),
            'mixed':b''.join(rng.randbytes(rng.randint(1,3000)) if rng.random()<0.3 else text_corpus(rng,rng.randint(1,6000)) for _ in range(60)),
        }
        strategies={'default':zlib.Z_DEFAULT_STRATEGY,'filtered':zlib.Z_FILTERED,'huffman':zlib.Z_HUFFMAN_ONLY,'rle':zlib.Z_RLE,'fixed':zlib.Z_FIXED}
        for kind,wbits,name in [(RAW,-15,'raw'),(ZLIB,15,'zlib'),(GZIP,31,'gzip')]:
            cases=[];expected=[]
            for corpus,data in corpora.items():
                for level in range(-1,10):
                    for strategy in strategies.values():
                        stream=compress(data,level,wbits,8,strategy);cases.append(stream);expected.append(data)
                        assert oracle(stream,wbits)==data
            agree(kind,cases,expected,name)
            print(f'PASS {name}: {len(cases)} streams = {len(corpora)} corpora x levels -1..9 (0 = stored) x 5 strategies match zlib',flush=True)

        # Window sizes, memory levels, flush points (empty stored and fixed blocks) and tiny inputs.
        cases=[];expected=[]
        for data in [corpora['text'],corpora['periods'],corpora['mixed']]:
            for wbits in range(9,16):
                for mem in (1,5,9):
                    cases.append(compress(data,9,-wbits,mem));expected.append(data)
            for mode in (zlib.Z_SYNC_FLUSH,zlib.Z_FULL_FLUSH,zlib.Z_PARTIAL_FLUSH,zlib.Z_BLOCK):
                c=zlib.compressobj(6,zlib.DEFLATED,-15);stream=b'';pieces=[data[i:i+7777] for i in range(0,len(data),7777)]
                for piece in pieces:stream+=c.compress(piece)+c.flush(mode)
                stream+=c.flush();cases.append(stream);expected.append(data);assert oracle(stream,-15)==data
        for size in range(0,300):
            data=corpora['text'][size*7:size*7+size];cases.append(compress(data,rng.choice([0,1,6,9]),-15,8,rng.choice(list(strategies.values()))));expected.append(data)
        agree(RAW,cases,expected,'windows/flushes')
        print(f'PASS raw: {len(cases)} streams over window sizes 2^9..2^15, memLevels, sync/full/partial/block flushes and 300 tiny inputs',flush=True)

        # Empty payloads in every container, and empty gzip input (no members).
        expect(RAW,compress(b'',6,-15),b'');expect(ZLIB,zlib.compress(b''),b'');expect(GZIP,gzip.compress(b''),b'');expect(GZIP,b'',b'')
        reject(RAW,b'',5);reject(ZLIB,b'',5)
        print('PASS empty payloads in raw/zlib/gzip; empty gzip input is empty output; empty raw/zlib input is truncated',flush=True)

        # Multi-megabyte inputs.
        big_text=text_corpus(rng,8_000_000);big_random=rng.randbytes(5_000_000)
        big_runs=b''.join(bytes([rng.randrange(256)])*rng.randint(1,2000) for _ in range(6000))
        for data,label in [(big_text,'8 MB text'),(big_random,'5 MB random'),(big_runs,f'{len(big_runs)//1000000} MB runs')]:
            for kind,wbits in [(RAW,-15),(ZLIB,15),(GZIP,31)]:
                stream=compress(data,6,wbits);ok,got=run(kind,stream);assert ok,got
                assert hashlib.sha256(got).digest()==hashlib.sha256(data).digest(),(label,kind)
        print('PASS multi-megabyte raw/zlib/gzip: 8 MB text, 5 MB random (stored blocks), RLE runs',flush=True)

        # Maximum distance (32768) and length (258), overlapping copies, invalid symbols.
        window=rng.randbytes(32768)
        crafted=[
            fixed_stream(list(window)+[(258,32768),(258,1),(3,32768),(258,32767),(257,32768),(258,2),(9,3)]),
            fixed_stream(list(window)+[('len284',32768),('len284',1),(258,32768)]),
            fixed_stream([7]+[(258,1)]*300),
            fixed_stream([1,2,3,4,5,6,7,8,9]+[(d+3,d) for d in range(1,10)]*40),
            fixed_stream(list(b'abc')+[(3,4)]),           # distance before the start of output
            fixed_stream([('sym',286)]),fixed_stream([('sym',287)]),   # invalid fixed literal/length codes
            fixed_stream([65,('dist',257,30)]),fixed_stream([65,('dist',257,31)]),  # invalid fixed distance codes
            fixed_stream([65,66],[(3,2)]),   # match across a block boundary
        ]
        wants=[oracle(case,-15) for case in crafted]
        assert wants[0] is not None and len(wants[0])==32768+1301 and wants[0][32768:33026]==window[:258]
        assert [w is None for w in wants]==[False,False,False,False,True,True,True,True,True,False]
        agree(RAW,crafted,wants,'crafted')
        agree(ZLIB,[zlib_wrap(c,w or b'') for c,w in zip(crafted,wants)],wants,'crafted zlib')
        print('PASS distance 32768 / length 258 (symbols 285 and 284+31), overlapping periods 1..9, cross-block match; too-far and 286/287/30/31 rejected',flush=True)

        # gzip headers and members.
        payload=corpora['text'][:50_000]
        members=[
            gzip_member(payload,flags=8,name=b'report.txt'),gzip_member(payload,flags=16,comment=b'a comment\xff'),
            gzip_member(payload,flags=4,extra=b'AP\x04\x00abcd'),gzip_member(payload,flags=2),
            gzip_member(payload,flags=1|2|4|8|16,name=b'n',comment=b'c',extra=b'x'*300,mtime=0x12345678),
            gzip_member(b'',flags=2|8,name=b'empty'),
        ]
        for member in members:
            want=gzip_oracle(member);assert want is not None and oracle(member,31)==want
            expect(GZIP,member,want)
        multi=gzip.compress(b'first member\n')+gzip_member(payload,flags=8,name=b'two')+gzip.compress(b'')+gzip.compress(corpora['random'][:20000])
        expect(GZIP,multi,gzip_oracle(multi));expect(GZIP,multi+b'\x00'*9,gzip_oracle(multi+b'\x00'*9))
        expect(GZIP,gzip.compress(b'a')+b'\x00\x00'+gzip.compress(b'b'),b'ab')
        reject(GZIP,multi+b'garbage',22);reject(GZIP,b'\x00'+gzip.compress(b'x'),22)
        reject(GZIP,gzip_member(payload,flags=2,header_crc=1234),74)
        reject(GZIP,gzip_member(payload,flags=32),22)
        bad=bytearray(gzip.compress(payload));bad[-5]^=1;reject(GZIP,bytes(bad),74)       # CRC-32
        bad=bytearray(gzip.compress(payload));bad[-1]^=1;reject(GZIP,bytes(bad),74)       # ISIZE
        bad=bytearray(gzip.compress(payload));bad[2]=7;reject(GZIP,bytes(bad),22)         # CM
        bad=bytearray(zlib.compress(payload));bad[-1]^=1;reject(ZLIB,bytes(bad),74)       # Adler-32
        reject(RAW,compress(payload,6,-15)+b'x',22);reject(ZLIB,zlib.compress(payload)+b'x',22)
        print('PASS gzip FNAME/FCOMMENT/FEXTRA/FHCRC/FTEXT, 4 concatenated members with zero padding; bad header CRC, flags, CRC-32, ISIZE, CM, Adler-32, trailing data rejected',flush=True)

        # Truncation: every prefix of small streams and sampled prefixes of large ones fail.
        streams=[(RAW,compress(corpora['text'][:30_000],9,-15)),(RAW,compress(corpora['random'][:5000],0,-15)),
                 (RAW,compress(corpora['repetitive'][:20_000],6,-15,8,zlib.Z_RLE)),(RAW,compress(b'hello hello hello',6,-15,8,zlib.Z_FIXED)),
                 (ZLIB,zlib.compress(corpora['source'][:30_000])),(GZIP,members[4]),(GZIP,multi)]
        total=0
        for kind,stream in streams:
            cuts=range(len(stream)) if len(stream)<600 else sorted(set(rng.sample(range(len(stream)),400))|set(range(40))|set(range(len(stream)-40,len(stream))))
            pairs=[(cut,stream[:cut]) for cut in cuts]
            # A multi-member prefix ending exactly at a member boundary is a complete file.
            if kind==GZIP:pairs=[(cut,case) for cut,case in pairs if gzip_oracle(case) is None]
            else:assert all(oracle(case,-15 if kind==RAW else 15) is None for cut,case in pairs)
            results=batch(kind,[case for cut,case in pairs]);total+=len(pairs)
            for (cut,case),result in zip(pairs,results):assert isinstance(result,tuple),(kind,cut,'accepted truncated stream')
        print(f'PASS {total} truncated prefixes rejected (raw dynamic/stored/RLE/fixed, zlib, gzip with every header field, multi-member)',flush=True)

        # Bit flips and random garbage: identical verdicts and outputs to zlib.
        flips=0
        sources=[(RAW,-15,compress(corpora['text'][:20_000],6,-15)),(RAW,-15,compress(corpora['periods'][:20_000],9,-15,8,zlib.Z_FIXED)),
                 (RAW,-15,compress(corpora['mixed'][:20_000],1,-15)),(RAW,-15,compress(corpora['repetitive'][:30_000],6,-15,8,zlib.Z_HUFFMAN_ONLY)),
                 (ZLIB,15,zlib.compress(corpora['source'][:20_000],9)),(GZIP,31,gzip.compress(corpora['text'][:20_000]))]
        for kind,wbits,stream in sources:
            cases=[]
            for _ in range(400):
                damaged=bytearray(stream)
                for _ in range(rng.choice([1,1,1,2,3])):
                    # Concentrate on block headers and Huffman tables, then anywhere.
                    at=rng.randrange(min(len(damaged),80)) if rng.random()<0.5 else rng.randrange(len(damaged))
                    damaged[at]^=1<<rng.randrange(8)
                cases.append(bytes(damaged))
            wants=[oracle(case,wbits) for case in cases];flips+=len(cases)
            agree(kind,cases,wants,f'flips {kind}')
        garbage=[rng.randbytes(rng.randint(1,64)) for _ in range(600)]+[bytes([rng.choice([4,5,0x0c,0x0d,0xec,0xed])])+rng.randbytes(rng.randint(1,200)) for _ in range(600)]
        agree(RAW,garbage,[oracle(g,-15) for g in garbage],'garbage')
        agree(ZLIB,[b'\x78\x9c'+g for g in garbage],[oracle(b'\x78\x9c'+g,15) for g in garbage],'garbage zlib')
        accepted=sum(oracle(g,-15) is not None for g in garbage)
        print(f'PASS {flips} bit-flipped streams and {len(garbage)*2} random/dynamic-header garbage inputs give zlib\'s verdict and output ({accepted} garbage inputs accepted by both), no traps',flush=True)

        # Output limit (error 27) and decompression bombs.
        data=corpora['text'][:100_000]
        for kind,stream in [(RAW,compress(data,6,-15)),(ZLIB,zlib.compress(data)),(GZIP,gzip.compress(data)),(RAW,compress(data,0,-15)),(RAW,compress(data,6,-15,8,zlib.Z_FIXED))]:
            expect(kind,stream,data,len(data))
            for limit in (len(data)-1,len(data)//2,1,0):reject(kind,stream,27,limit)
        expect(GZIP,multi,gzip_oracle(multi),len(gzip_oracle(multi)));reject(GZIP,multi,27,len(gzip_oracle(multi))-1)
        expect(RAW,compress(b'',6,-15),b'',0)
        bomb=gzip.compress(bytes(200_000_000),9)
        started=time.monotonic();reject(GZIP,bomb,27,1<<20);elapsed=time.monotonic()-started
        assert elapsed<5,elapsed
        reject(RAW,b'\x03\x00',22,-1)
        for kind,stream in [(RAW,compress(data,6,-15)),(ZLIB,zlib.compress(data)),(GZIP,gzip.compress(data))]:expect(kind,stream,data,(1<<63)-1)
        ok,got=run(HTTP,b'gzip\n'+gzip.compress(data),(1<<63)-1);assert ok and got==data
        print(f'PASS output limit: exact limit accepted, limit-1/half/1/0 give error 27 in raw/zlib/gzip/stored/fixed/multi-member, i64-max limit accepted, negative rejected; {len(bomb)} byte gzip bomb (200 MB) stopped at 1 MiB in {elapsed*1000:.0f} ms',flush=True)

        # zlib preset dictionary and header checks.
        fdict=compress(b'hello hello hello',6,15,zdict=b'hello')
        assert fdict[1]&0x20
        reject(ZLIB,fdict,95)
        reject(ZLIB,b'\x78\x9d'+zlib.compress(b'x')[2:],22)       # FCHECK
        assert zlib_header(0x78,0x80)==b'\x78\x9c'
        reject(ZLIB,zlib_header(0x79)+zlib.compress(b'x')[2:],22)  # CM=9
        reject(ZLIB,zlib_header(0x88)+zlib.compress(b'x')[2:],22)  # CINFO=8 (64 KiB window)
        expect(ZLIB,zlib_header(0x08)+zlib.compress(b'x')[2:],b'x')  # CINFO=0 (256-byte window) is valid
        print('PASS zlib FDICT rejected with error 95; FCHECK, CM and CINFO violations rejected',flush=True)

        # HTTP Content-Encoding.
        body=corpora['source'][:60_000]
        def http(encoding,stream,limit=LIMIT):return run(HTTP,encoding+b'\n'+stream,limit)
        for encoding,stream in [(b'gzip',gzip.compress(body)),(b'x-gzip',gzip.compress(body)),(b' GZip ',gzip.compress(body)),
                                (b'deflate',zlib.compress(body)),(b'Deflate',compress(body,6,-15)),(b'identity',body),(b'',body),
                                (b'deflate, gzip',gzip.compress(zlib.compress(body))),(b'gzip,identity',gzip.compress(body)),
                                (b'x-gzip , deflate',compress(gzip.compress(body),9,-15))]:
            ok,got=http(encoding,stream);assert ok and got==body,(encoding,got if not ok else len(got))
        for encoding in (b'gzip',b'deflate',b'identity',b'x-gzip, deflate'):
            ok,got=http(encoding,b'');assert ok and got==b'',(encoding,got)
        ok,got=http(b'br',body);assert not ok and got[0]==95
        ok,got=http(b'gzip',body);assert not ok and got[0]==22
        ok,got=http(b'deflate',compress(body,6,-15)[:-3]);assert not ok
        ok,got=http(b'deflate',zlib.compress(bytes(10_000_000)),1000);assert not ok and got[0]==27
        ok,got=http(b'deflate',compress(bytes(10_000_000),6,-15),1000);assert not ok and got[0]==27
        ok,got=http(b'identity',body,100);assert not ok and got[0]==27
        print('PASS http_content_decode: gzip/x-gzip/deflate(zlib, raw fallback)/identity, case and whitespace, stacked codings, empty bodies; br, bad data and limits rejected',flush=True)

        # Throughput on a few-MB file: decoded MB/s, best of 5 interleaved trials of
        # 10 in-process decodes each, Neo against Python's zlib (C) module.
        bench=text_corpus(random.Random(7),3_000_000)+source_corpus()[:1_000_000];reps=10
        streams={'gzip':(12,31,gzip.compress(bench,6)),'raw deflate':(10,-15,compress(bench,6,-15))}
        best={}
        for _ in range(5):
            for name,(mode,wbits,stream) in streams.items():
                ok,got=run(mode,stream,LIMIT,reps);assert ok
                nanos,total=map(int,got.split());assert total==len(bench)*reps
                best[name,'neo']=max(best.get((name,'neo'),0),len(bench)*reps/(nanos/1e9)/1e6)
                started=time.perf_counter()
                for _ in range(reps):out=zlib.decompress(stream,wbits)
                elapsed=time.perf_counter()-started;assert out==bench
                best[name,'python']=max(best.get((name,'python'),0),len(bench)*reps/elapsed/1e6)
        for name,(mode,wbits,stream) in streams.items():
            neo,python=best[name,'neo'],best[name,'python']
            print(f'PASS throughput {name}: {len(stream)/1e6:.2f} MB -> {len(bench)/1e6:.2f} MB, Neo {neo:.0f} MB/s, Python zlib {python:.0f} MB/s ({neo/python:.2f}x)',flush=True)
        print(f'PASS deflate language: {counts["cases"]} decoder runs',flush=True)


if __name__=='__main__':
    main()
