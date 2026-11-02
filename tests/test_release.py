import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from neoc.release import bundle


class Release(unittest.TestCase):
    def test_archive_is_reproducible_and_manifest_covers_every_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.tar.gz';b=Path(tmp)/'b.tar.gz';ra=bundle(a);rb=bundle(b)
            self.assertEqual(ra['sha256'],rb['sha256'])
            with tarfile.open(a) as tar:
                members=tar.getmembers();manifest=json.load(tar.extractfile(next(m for m in members if m.name.endswith('/MANIFEST.json'))))
                actual={}
                for item in members:
                    name=item.name.split('/',1)[1]
                    self.assertNotIn('..',Path(item.name).parts);self.assertFalse(item.issym());self.assertEqual(item.uid,0)
                    if name!='MANIFEST.json':actual[name]=hashlib.sha256(tar.extractfile(item).read()).hexdigest()
                self.assertEqual(actual,manifest['files']);self.assertFalse(any(n.startswith('examples/') for n in actual))
                self.assertIn('skills.md',actual);self.assertEqual(next(m for m in members if m.name.endswith('/neo')).mode,0o755)


if __name__=='__main__':unittest.main()
