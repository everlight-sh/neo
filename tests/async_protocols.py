"""Native cooperative HTTP, verified TLS and DNS with independent delayed peers."""
import argparse,contextlib,http.server,os,select,socket,ssl,subprocess,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Server(http.server.ThreadingHTTPServer):
    request_queue_size=128
    daemon_threads=True
class Peer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        deadline=time.monotonic()+(.30 if self.path=='/tls' else .15 if self.path=='/http' else 3)
        if self.path=='/hold':
            while time.monotonic()<deadline:
                if select.select([self.connection],[],[],.02)[0] and not self.connection.recv(1,socket.MSG_PEEK):return
        else:time.sleep(max(0,deadline-time.monotonic()))
        body=b'TLS OK' if self.path=='/tls' else b'HTTP OK'
        try:self.send_response(200);self.send_header('Content-Length',str(len(body)));self.send_header('Connection','close');self.end_headers();self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,*_):pass

def command(*args):subprocess.run(['openssl',*map(str,args)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def certificates(root):
    command('req','-new','-x509','-newkey','rsa:2048','-nodes','-keyout',root/'ca.key','-out',root/'ca.pem','-subj','/CN=Neo Async Test CA','-days','2','-sha256','-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign')
    command('req','-new','-newkey','rsa:2048','-nodes','-keyout',root/'leaf.key','-out',root/'leaf.csr','-subj','/CN=localhost')
    (root/'extensions').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n')
    command('x509','-req','-in',root/'leaf.csr','-CA',root/'ca.pem','-CAkey',root/'ca.key','-CAcreateserial','-out',root/'leaf.pem','-days','1','-sha256','-extfile',root/'extensions')
    command('x509','-in',root/'ca.pem','-outform','DER','-out',root/'ca.der')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binary',type=Path,default=ROOT/'build/async-protocols');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='neo-async-protocols-') as temporary:
        root=Path(temporary);certificates(root);plain=Server(('127.0.0.1',0),Peer);secure=Server(('127.0.0.1',0),Peer)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_3;context.maximum_version=ssl.TLSVersion.TLSv1_3;context.load_cert_chain(str(root/'leaf.pem'),str(root/'leaf.key'));context.set_alpn_protocols(['http/1.1']);secure.socket=context.wrap_socket(secure.socket,server_side=True)
        for server in (plain,secure):threading.Thread(target=server.serve_forever,daemon=True).start()
        dns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);dns.bind(('127.0.0.1',0));dns.settimeout(10)
        def nameserver():
            try:
                query,source=dns.recvfrom(4096);time.sleep(.1);reply=query[:2]+b'\x81\x80\0\1\0\1\0\0\0\0'+query[12:]+b'\xc0\x0c\0\1\0\1\0\0\0\x3c\0\4\x7f\0\0\1';dns.sendto(reply,source)
            except OSError:pass
        worker=threading.Thread(target=nameserver,daemon=True);worker.start()
        try:
            result=subprocess.run([str(args.binary.resolve())],env={**os.environ,'NEO_THREADS':'1','NEO_ASYNC_HTTP_PORT':str(plain.server_port),'NEO_ASYNC_TLS_PORT':str(secure.server_port),'NEO_ASYNC_DNS_PORT':str(dns.getsockname()[1]),'NEO_ASYNC_CA':str(root/'ca.der')},capture_output=True,text=True,timeout=15)
            assert result.returncode==0,(result.returncode,result.stdout,result.stderr);assert result.stdout.endswith('42\n'),result.stdout
            print('PASS verified TLS 1.3 + HTTP + DNS suspended call stacks, await deadlines and resource cleanup:',result.stdout.strip(),flush=True)
        finally:
            dns.close()
            for server in (plain,secure):server.shutdown();server.server_close()
if __name__=='__main__':main()
