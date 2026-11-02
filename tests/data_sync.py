#!/usr/bin/env python3
"""Data persistence barriers preserve contents and report kernel failures."""
import os,platform,subprocess,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(prefix='neo-data-sync-') as temporary:
        p=Path(temporary);binary=p/'probe'
        r=subprocess.run(['python3','-m','neoc','build',str(ROOT/'tests/fixtures/data_sync.neo'),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
        assert r.returncode==0,(json.loads(r.stdout).get('errors') if r.stdout.startswith('{') else r.stdout[-3000:],r.stderr[-3000:])
        r=subprocess.run([str(binary),str(p/'data')],capture_output=True,text=True,timeout=30)
        assert r.returncode==0 and r.stdout=='ok\n',(r.returncode,r.stdout,r.stderr)
        assert (p/'data').read_bytes()==b'FIRST-second'
        assert not subprocess.check_output(['nm','-u',str(binary)],text=True).strip()
        if platform.system()=='Linux':
            assert 'INTERP' not in subprocess.check_output(['readelf','-l',str(binary)],text=True)
            assert 'NEEDED' not in subprocess.check_output(['readelf','-d',str(binary)],text=True)
            import ctypes,errno
            class Filter(ctypes.Structure):_fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]
            class Program(ctypes.Structure):_fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
            syscall=83 if platform.machine() in ('aarch64','arm64') else 75
            def inject():
                libc=ctypes.CDLL(None,use_errno=True);rules=(Filter*4)(Filter(0x20,0,0,0),Filter(0x15,0,1,syscall),Filter(0x06,0,0,0x50000|errno.EIO),Filter(0x06,0,0,0x7fff0000));program=Program(4,rules)
                assert libc.prctl(38,1,0,0,0)==0
                assert libc.prctl(22,2,ctypes.byref(program))==0
            r=subprocess.run([str(binary),str(p/'fault')],capture_output=True,text=True,preexec_fn=inject,timeout=30)
            assert r.returncode!=0,(r.stdout,r.stderr)
    print('PASS data sync: new/grown/overwritten file contents, EBADF and dependency audit'+('; native barrier EIO' if platform.system()=='Linux' else ''),flush=True)
if __name__=='__main__':main()
