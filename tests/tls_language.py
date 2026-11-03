#!/usr/bin/env python3
"""Independent X.509 and TLS peers, corruption and fragmentation tests."""
import contextlib
import hashlib
import hmac
import json
import os
from pathlib import Path
import random
import shlex
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
RUNNER=shlex.split(os.environ.get('NEO_RUNNER',''))


def openssl(*args,data=None):
    r=subprocess.run(['openssl',*map(str,args)],input=data,capture_output=True,timeout=60)
    assert r.returncode==0,r.stderr
    return r.stdout


def default_suite():
    """The TLS 1.3 suite the client lists first: AES-128-GCM (4865) when the client's aes_hardware()
    is true (x86-64 with AES-NI, PCLMULQDQ and SSE4.1; Linux AArch64 with AES and PMULL), otherwise
    ChaCha20-Poly1305 (4867)."""
    import platform
    machine = platform.machine().lower()
    if machine in ('aarch64', 'arm64') and sys.platform.startswith('linux'):
        try: features = set(next(line for line in open('/proc/cpuinfo') if line.startswith('Features')).split(':', 1)[1].split())
        except (OSError, StopIteration): return 4867
        return 4865 if {'aes', 'pmull'} <= features else 4867
    if machine not in ('x86_64', 'amd64'): return 4867
    try: flags = set(next(line for line in open('/proc/cpuinfo') if line.startswith('flags')).split())
    except (OSError, StopIteration):
        r = subprocess.run(['sysctl', '-n', 'machdep.cpu.features'], capture_output=True, text=True)
        flags = {flag.lower().replace('.', '_') for flag in r.stdout.split()}
    return 4865 if {'aes', 'pclmulqdq', 'sse4_1', 'ssse3'} <= flags else 4867


def certificates(root):
    openssl('req','-new','-x509','-newkey','rsa:2048','-nodes','-keyout',root/'ca.key','-out',root/'ca.pem','-subj','/CN=Neo Test Root','-days','2','-sha256',
        '-addext','basicConstraints=critical,CA:TRUE,pathlen:1','-addext','keyUsage=critical,keyCertSign,cRLSign')
    openssl('req','-new','-newkey','rsa:2048','-nodes','-keyout',root/'leaf.key','-out',root/'leaf.csr','-subj','/CN=localhost')
    variants={'leaf':'','unknown':'1.2.3.4.5=critical,DER:05:00\n','wrong-eku':'','wildcard':'','ca-leaf':''}
    for name,extra in variants.items():
        config='basicConstraints=critical,CA:'+('TRUE' if name=='ca-leaf' else 'FALSE')+'\nkeyUsage=critical,digitalSignature\nextendedKeyUsage='+('clientAuth' if name=='wrong-eku' else 'serverAuth')+'\nsubjectAltName='+('DNS:*.example.test' if name=='wildcard' else 'DNS:localhost,IP:127.0.0.1')+'\n'+extra
        (root/'extensions').write_text(config)
        openssl('x509','-req','-in',root/'leaf.csr','-CA',root/'ca.pem','-CAkey',root/'ca.key','-CAcreateserial','-out',root/(name+'.pem'),'-days','1','-sha256','-extfile',root/'extensions')
    for name in ['ca',*variants]:openssl('x509','-in',root/(name+'.pem'),'-outform','DER','-out',root/(name+'.der'))
    openssl('req','-new','-newkey','rsa:2048','-nodes','-keyout',root/'middle.key','-out',root/'middle.csr','-subj','/CN=Neo Test Intermediate')
    for name,usage in [('middle','keyCertSign,cRLSign'),('middle-wrong-ku','digitalSignature')]:
        (root/'extensions').write_text('basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,'+usage+'\n')
        openssl('x509','-req','-in',root/'middle.csr','-CA',root/'ca.pem','-CAkey',root/'ca.key','-CAcreateserial','-out',root/(name+'.pem'),'-days','1','-sha256','-extfile',root/'extensions')
        openssl('x509','-in',root/(name+'.pem'),'-outform','DER','-out',root/(name+'.der'))
    (root/'extensions').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost\n')
    openssl('x509','-req','-in',root/'leaf.csr','-CA',root/'middle.pem','-CAkey',root/'middle.key','-CAcreateserial','-out',root/'middle-leaf.pem','-days','1','-sha256','-extfile',root/'extensions')
    openssl('x509','-in',root/'middle-leaf.pem','-outform','DER','-out',root/'middle-leaf.der')
    (root/'intermediate-chain.pem').write_bytes((root/'middle-leaf.pem').read_bytes()+(root/'middle.pem').read_bytes())
    openssl('req','-new','-x509','-key',root/'ca.key','-out',root/'zero-ca.pem','-subj','/CN=Neo Test Root','-days','2','-sha256',
        '-addext','basicConstraints=critical,CA:TRUE,pathlen:0','-addext','keyUsage=critical,keyCertSign,cRLSign')
    openssl('x509','-in',root/'zero-ca.pem','-outform','DER','-out',root/'zero-ca.der')
    corrupted=bytearray((root/'leaf.der').read_bytes());corrupted[-1]^=1;(root/'signature.der').write_bytes(corrupted)
    openssl('x509','-inform','DER','-in',root/'signature.der','-out',root/'signature.pem')
    openssl('req','-new','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes','-keyout',root/'ec-ca.key','-out',root/'ec-ca.pem','-subj','/CN=Neo EC Test Root','-days','2','-sha256',
        '-addext','basicConstraints=critical,CA:TRUE,pathlen:1','-addext','keyUsage=critical,keyCertSign,cRLSign')
    openssl('req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes','-keyout',root/'ec-leaf.key','-out',root/'ec-leaf.csr','-subj','/CN=localhost')
    (root/'extensions').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n')
    for name,csr,issuer in [('ec-leaf','ec-leaf','ec-ca'),('ec-cross','ec-leaf','ca'),('rsa-ec','leaf','ec-ca')]:
        openssl('x509','-req','-in',root/(csr+'.csr'),'-CA',root/(issuer+'.pem'),'-CAkey',root/(issuer+'.key'),'-CAcreateserial','-out',root/(name+'.pem'),'-days','1','-sha256','-extfile',root/'extensions')
        openssl('x509','-in',root/(name+'.pem'),'-outform','DER','-out',root/(name+'.der'))
    openssl('x509','-in',root/'ec-ca.pem','-outform','DER','-out',root/'ec-ca.der')
    return root


def hkdf_label(secret,label,size):
    label=b'tls13 '+label
    info=size.to_bytes(2,'big')+bytes([len(label)])+label+b'\0'
    return hmac.digest(secret,info+b'\1','sha256')[:size]


def encrypted_record(secret,sequence,kind,payload):
    key=hkdf_label(secret,b'key',32);iv=hkdf_label(secret,b'iv',12)
    nonce=bytes(a^b for a,b in zip(iv,sequence.to_bytes(12,'big')));plain=payload+bytes([kind])
    ciphertext=openssl('enc','-chacha20','-K',key.hex(),'-iv',((1).to_bytes(4,'little')+nonce).hex(),'-nosalt',data=plain)
    header=b'\x17\x03\x03'+(len(ciphertext)+16).to_bytes(2,'big')
    polykey=openssl('enc','-chacha20','-K',key.hex(),'-iv',(bytes(4)+nonce).hex(),'-nosalt',data=bytes(32))
    mac=header+bytes((-len(header))%16)+ciphertext+bytes((-len(ciphertext))%16)+len(header).to_bytes(8,'little')+len(ciphertext).to_bytes(8,'little')
    tag=bytes.fromhex(openssl('mac','-macopt','hexkey:'+polykey.hex(),'POLY1305',data=mac).decode().strip())
    return header+ciphertext+tag


@contextlib.contextmanager
def peer(root,name='leaf',case='normal',fragment=0):
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_3;context.maximum_version=ssl.TLSVersion.TLSv1_3
    if case=='legacy':context.minimum_version=ssl.TLSVersion.TLSv1_2;context.maximum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(root/(name+'.pem')),str(root/('ec-leaf.key' if name in ('ec-leaf','ec-cross') else 'leaf.key')));context.set_alpn_protocols(['http/1.1'])
    keylog=root/('keys-'+str(time.monotonic_ns()));context.keylog_filename=str(keylog)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(5);errors=[];received=[]
    def serve():
        try:
            conn,_=listener.accept()
            with conn:
                conn.settimeout(5);incoming=ssl.MemoryBIO();outgoing=ssl.MemoryBIO();secure=context.wrap_bio(incoming,outgoing,server_side=True)
                encrypted_count=0
                def send_wire(data,mutate=False):
                    nonlocal encrypted_count
                    if mutate and data:
                        # Corrupt the first ciphertext record, preserving framing.
                        p=0
                        while p+5<=len(data):
                            size=int.from_bytes(data[p+3:p+5],'big')
                            if data[p]==23 and p+5+size<=len(data):data=data[:p+4+size]+bytes([data[p+4+size]^1])+data[p+5+size:];break
                            p+=5+size
                    p=0
                    while p+5<=len(data):
                        size=int.from_bytes(data[p+3:p+5],'big')
                        if data[p]==23:encrypted_count+=1
                        p+=5+size
                    if fragment:
                        for at in range(0,len(data),fragment):conn.sendall(data[at:at+fragment])
                    else:conn.sendall(data)
                def flush(mutate=False):
                    wire=outgoing.read()
                    if wire:send_wire(wire,mutate)
                while True:
                    try:secure.do_handshake();break
                    except ssl.SSLWantReadError:
                        flush(case=='handshake-tag');raw=conn.recv(16384)
                        if not raw:return
                        incoming.write(raw)
                if case=='legacy':assert secure.version()=='TLSv1.2' and secure.cipher()[0].startswith('ECDHE-RSA-'),secure.cipher()
                else:
                    assert secure.version()=='TLSv1.3'
                    assert secure.cipher()[0]=='TLS_CHACHA20_POLY1305_SHA256'
                # Session tickets use application traffic keys and precede data.
                app_records=0
                wire=outgoing.read()
                if wire:
                    at=0
                    while at+5<=len(wire):app_records+=wire[at]==23;at+=5+int.from_bytes(wire[at+3:at+5],'big')
                    send_wire(wire)
                message=b''
                while not message.endswith(b'\n'):
                    try:message+=secure.read(16384)
                    except ssl.SSLWantReadError:
                        flush();raw=conn.recv(16384)
                        if not raw:return
                        incoming.write(raw)
                received.append(message);assert message==b'Neo TLS\n'
                if case=='timeout':time.sleep(2.5);return
                if case=='key-update':
                    lines=keylog.read_text().splitlines();secret=bytes.fromhex(next(s.split()[2] for s in lines if s.startswith('SERVER_TRAFFIC_SECRET_0 ')))
                    # OpenSSL emits two TLS 1.3 tickets after receiving Finished.
                    # Determine their count from the ciphertext already sent after handshake.
                    send_wire(encrypted_record(secret,app_records,22,b'\x18\0\0\x01\x01'))
                    next_secret=hkdf_label(secret,b'traffic upd',32)
                    send_wire(encrypted_record(next_secret,0,23,b'secure echo\n'))
                    while True:
                        try:
                            if not secure.read(1):return
                        except ssl.SSLWantReadError:
                            raw=conn.recv(16384)
                            if not raw:return
                            incoming.write(raw)
                secure.write(b'secure echo\n');wire=outgoing.read()
                if case=='application-tag':wire=wire[:-1]+bytes([wire[-1]^1])
                if case=='truncated':wire=wire[:len(wire)//2]
                send_wire(wire)
                if case=='no-close' or case=='truncated' or case=='application-tag':return
                if case=='close':
                    try:secure.unwrap()
                    except ssl.SSLWantReadError:flush()
                    return
                # Consume a graceful client close when it arrives.
                try:
                    raw=conn.recv(16384)
                    if raw:incoming.write(raw);secure.read(1)
                except (ssl.SSLError,ConnectionResetError):pass
        except (ssl.SSLError,ConnectionResetError,BrokenPipeError) as ex:
            if case not in ('normal','close','key-update','legacy') or name!='leaf':return
            errors.append(repr(ex))
        except Exception as ex:errors.append(repr(ex))
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    try:yield listener.getsockname()[1],received
    finally:
        thread.join(7);listener.close();assert not thread.is_alive();assert not errors,errors


def main():
    with tempfile.TemporaryDirectory(prefix='neo-tls-language-') as tmp:
        root=certificates(Path(tmp));binaries={}
        for name in ('x509','tls'):
            binary=root/name;r=subprocess.run(['python3','-m','neoc','build','tests/fixtures/language_'+name+'.neo','-o',str(binary),'--report'],cwd=ROOT,capture_output=True,text=True)
            assert r.returncode==0,(json.loads(r.stdout).get('errors'),r.stderr);assert json.loads(r.stdout)['undefined_symbols']==[];binaries[name]=binary
        ca=(root/'ca.der').read_bytes();leaf=(root/'leaf.der').read_bytes();now=int(time.time())
        def verify(cert,host='localhost',timestamp=now,middle=b'',trust=ca):
            payload=bytes([len(host)])+host.encode()+timestamp.to_bytes(4,'big')+b''.join(len(c).to_bytes(3,'big')+c for c in (cert,middle,trust))
            result=subprocess.run(RUNNER+[str(binaries['x509'])],input=payload,capture_output=True,timeout=5);assert result.returncode==0,result.stderr
            return result.stdout==b'verified\n'
        assert verify(leaf);assert verify(leaf,'127.0.0.1');assert not verify(leaf,'evil.test');assert not verify(leaf,timestamp=0);assert not verify(leaf,timestamp=now+86400*4)
        for name in ('unknown','wrong-eku','ca-leaf','signature'):assert not verify((root/(name+'.der')).read_bytes()),name
        wildcard=(root/'wildcard.der').read_bytes();assert verify(wildcard,'one.example.test');assert not verify(wildcard,'two.one.example.test');assert not verify(wildcard,'example.test')
        middle_leaf=(root/'middle-leaf.der').read_bytes();middle=(root/'middle.der').read_bytes();zero=(root/'zero-ca.der').read_bytes()
        assert verify(middle_leaf,middle=middle);assert not verify(middle_leaf)
        assert verify(leaf,trust=zero);assert not verify(middle_leaf,middle=middle,trust=zero)
        assert not verify(middle_leaf,middle=(root/'middle-wrong-ku.der').read_bytes())
        ec_trust=(root/'ec-ca.der').read_bytes()
        for name,trust in [('ec-leaf',ec_trust),('ec-cross',ca),('rsa-ec',ec_trust)]:
            cert=(root/(name+'.der')).read_bytes()
            assert verify(cert,trust=trust),name
            bad=cert[:-1]+bytes([cert[-1]^1]);assert not verify(bad,trust=trust),name
        assert not verify((root/'ec-leaf.der').read_bytes())
        rng=random.Random(52808439)
        for _ in range(150):
            bad=rng.randbytes(rng.randrange(0,512));assert not verify(bad)
        for length in range(0,len(leaf),max(1,len(leaf)//30)):assert not verify(leaf[:length])
        print('PASS X.509: trusted RSA certificates, DNS/IP SAN, wildcard boundaries, times, critical extensions, EKU, CA rules, bad signatures and 180+ malformed/truncated inputs',flush=True)
        def client(port,host='localhost',drain=False,trust='ca'):
            args=[str(binaries['tls']),str(port),str(root/(trust+'.der')),host]+(['drain'] if drain else [])
            r=subprocess.run(RUNNER+args,capture_output=True,text=True,timeout=8);assert r.returncode==0,(r.stdout,r.stderr)
            return r.stdout
        for fragment in (0,1,7):
            with peer(root,fragment=fragment) as (port,received):assert client(port)=='secure echo\n';assert received==[b'Neo TLS\n']
        with peer(root,name='intermediate-chain') as (port,received):assert client(port)=='secure echo\n'
        with peer(root,name='wildcard') as (port,received):assert client(port,'one.example.test')=='secure echo\n'
        for name,trust in [('ec-leaf','ec-ca'),('ec-cross','ca'),('rsa-ec','ec-ca')]:
            with peer(root,name=name) as (port,received):assert client(port,trust=trust)=='secure echo\n';assert received==[b'Neo TLS\n']
        with peer(root,case='close') as (port,received):assert client(port,drain=True)=='secure echo\n'
        for name,host in [('leaf','evil.test'),('unknown','localhost'),('wrong-eku','localhost'),('signature','localhost')]:
            with peer(root,name=name,case='reject') as (port,received):assert client(port,host).startswith('rejected:');assert not received
        # A TLS 1.2-only peer is accepted over the client's TLS 1.2 path (tests/tls12_language.py covers it in depth).
        with peer(root,case='legacy') as (port,received):assert client(port)=='secure echo\n';assert received==[b'Neo TLS\n']
        with peer(root,case='handshake-tag') as (port,received):assert client(port).startswith('rejected:');assert not received
        for case in ('application-tag','truncated','no-close','timeout'):
            with peer(root,case=case) as (port,received):
                result=client(port,drain=True);assert result.startswith('read rejected:'),(case,result);assert 'secure echo' not in result
        with peer(root,case='key-update') as (port,received):assert client(port)=='secure echo\n'
        print('PASS TLS 1.3: RSA/ECDSA and mixed issuer chains, independent encrypted peer, byte fragmentation, tickets, close-notify, hostname/chain rejection, corrupt tags, truncation, deadlines and KeyUpdate; a TLS 1.2-only peer over TLS 1.2',flush=True)


if __name__=='__main__':main()
