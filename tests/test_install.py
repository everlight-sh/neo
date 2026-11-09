"""install.sh against a locally built release: from an archive, and downloaded
from a local server with its SHA256SUMS, where a wrong checksum installs nothing."""
import hashlib
import http.server
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from neoc.packages import VERSION
from neoc.release import bundle, native_platform
from test_driver import tools

ROOT=Path(__file__).resolve().parents[1]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class Install(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native=Path(os.environ.get('NEOC') or ROOT/'.neo-build/bin/neoc')
        if not native.is_file():raise unittest.SkipTest('set NEOC to a native compiler')
        platform=native_platform(native.read_bytes())
        cls.tmp=tempfile.TemporaryDirectory();releases=Path(cls.tmp.name)/'releases'
        cls.path=tools(Path(cls.tmp.name)/'tools','readlink','dirname','uname','mktemp','tar','gzip','cat','mkdir','rm',
                       'mv','ln','sha256sum','shasum','cut','awk','curl','wget','clang','ld')
        good=releases/('v'+VERSION);good.mkdir(parents=True)
        cls.archive=good/f'neo-{VERSION}-{platform}.tar.gz';bundle(cls.archive,native=native)
        (good/'SHA256SUMS').write_text(hashlib.sha256(cls.archive.read_bytes()).hexdigest()+f'  {cls.archive.name}\n')
        bad=releases/'v9.9.9';bad.mkdir();bad_name=f'neo-9.9.9-{platform}.tar.gz'
        shutil.copyfile(cls.archive,bad/bad_name)
        (bad/'SHA256SUMS').write_text('0'*64+f'  {bad_name}\n')
        handler=lambda *args:Quiet(*args,directory=str(releases))
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()

    def install(self,home,*args):
        return subprocess.run(['/bin/sh',str(ROOT/'install.sh'),*args],capture_output=True,text=True,timeout=600,
                              env={'PATH':str(self.path),'NEO_HOME':str(home),'NEO_DOWNLOAD_URL':f'http://127.0.0.1:{self.server.server_port}'})

    def version(self,home):
        return subprocess.run([str(home/'bin/neo'),'version'],cwd=home,capture_output=True,text=True,env={'PATH':str(self.path)}).stdout.strip()

    def test_an_archive_installs_runs_and_reinstalls(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'neo';first=self.install(home,'--archive',str(self.archive))
            self.assertEqual(first.returncode,0,first.stderr);self.assertIn('Clang ',first.stdout)
            self.assertEqual(self.version(home),'Neo '+VERSION)
            source=Path(tmp)/'hello.neo';source.write_text('fn main() -> i64 = 42\n')
            built=subprocess.run([str(home/'bin/neo'),'build',str(source),'-o',str(home/'hello')],cwd=tmp,
                                 capture_output=True,text=True,timeout=180,env={'PATH':str(self.path),'NEO_RUNTIME':str(home/'missing.o')})
            self.assertEqual(built.returncode,0,(built.stdout,built.stderr))
            self.assertEqual(subprocess.check_output([home/'hello'],text=True),'42\n')
            again=self.install(home,'--archive',str(self.archive));self.assertEqual(again.returncode,0,again.stderr)
            self.assertEqual([p.name for p in (home/'versions').iterdir()],[VERSION]);self.assertEqual(self.version(home),'Neo '+VERSION)

    def test_a_download_is_checked_against_sha256sums(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'neo';result=self.install(home,'--version',VERSION)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(self.version(home),'Neo '+VERSION)

    def test_a_wrong_checksum_installs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'neo';result=self.install(home,'--version','9.9.9')
            self.assertEqual(result.returncode,1);self.assertIn('checksum mismatch',result.stderr);self.assertFalse(home.exists())

    def test_a_requested_version_must_match_the_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=self.install(Path(tmp)/'neo','--archive',str(self.archive),'--version','9.9.9')
            self.assertEqual(result.returncode,1);self.assertIn(f'holds Neo {VERSION}, not 9.9.9',result.stderr)


if __name__=='__main__':unittest.main()
