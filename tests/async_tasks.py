"""A contended database/file lock must not block a task's independent peers."""
import argparse,fcntl,os,subprocess,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path,default=ROOT/'build/async-tasks');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='neo-async-lock-') as temporary:
        path=Path(temporary)/'lock';fd=os.open(path,os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
        def unlock():time.sleep(.25);fcntl.flock(fd,fcntl.LOCK_UN)
        thread=threading.Thread(target=unlock);thread.start()
        try:
            result=subprocess.run([str(args.binary.resolve())],env={**os.environ,'NEO_THREADS':'1','NEO_ASYNC_LOCK_FILE':str(path)},capture_output=True,text=True,timeout=4)
            assert result.returncode==0 and result.stdout=='42\n',(result.returncode,result.stdout,result.stderr)
            print('PASS nested tasks, independent timer progress during a contended file lock, and normal resource cleanup',flush=True)
        finally:thread.join();os.close(fd)
if __name__=='__main__':main()
