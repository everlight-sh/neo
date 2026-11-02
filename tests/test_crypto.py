import hashlib
import hmac
from pathlib import Path
import tempfile
import unittest
from neoc.modules import sources
from neoc.graph import hash_program
from neoc.check import Checker
from neoc.reference import Reference


class CryptographicVectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'main.neo';file.write_text('import "std:chacha20" import "std:sha1" fn main() -> i64 = 0')
            cls.program=sources(file);hash_program(cls.program);Checker(cls.program).run()

    def reference(self):return Reference(self.program,budget=20000000)

    def test_sha256_boundaries_against_hashlib(self):
        for n in (0,1,3,55,56,63,64,65,127,128,129,255):
            message=bytes(i%256 for i in range(n))
            with self.subTest(n=n):self.assertEqual(bytes(self.reference().call('sha256',[list(message)])),hashlib.sha256(message).digest())

    def test_hmac_against_independent_implementation(self):
        for key in (b'',b'key',b'\x0b'*20,bytes(range(256))):
            message=b'Hi There'
            with self.subTest(key=len(key)):self.assertEqual(bytes(self.reference().call('hmac_sha256',[list(key),list(message)])),hmac.digest(key,message,'sha256'))

    def test_legacy_sha1_boundaries(self):
        for n in (0,1,3,55,56,63,64,65,127,128,129,255):
            message=bytes(i%256 for i in range(n))
            self.assertEqual(bytes(self.reference().call('sha1',[list(message)])),hashlib.sha1(message).digest())

    def test_legacy_hmac_sha1(self):
        for key in (b'',b'key',b'\x0b'*20,bytes(range(256))):
            self.assertEqual(bytes(self.reference().call('hmac_sha1',[list(key),list(b'Hi There')])),hmac.digest(key,b'Hi There','sha1'))

    def test_rfc5869_hkdf_case_one(self):
        ikm=b'\x0b'*22;salt=bytes.fromhex('000102030405060708090a0b0c');info=bytes.fromhex('f0f1f2f3f4f5f6f7f8f9')
        expected_prk=bytes.fromhex('077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5')
        expected_okm=bytes.fromhex('3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865')
        reference=self.reference();prk=bytes(reference.call('hkdf_extract',[list(salt),list(ikm)]));self.assertEqual(prk,expected_prk)
        self.assertEqual(bytes(reference.call('hkdf_expand',[list(prk),list(info),42])),expected_okm)

    def test_rfc8439_block_and_poly1305(self):
        expected=bytes.fromhex('10f1e7e4d13b5915500fdd1fa32071c4c7d1f4c733c068030422aa9ac3d46c4ed2826446079faa0914c2d705d98b02a2b5129cd1de164eb9cbd083e8a2503c4e')
        reference=self.reference()
        self.assertEqual(bytes(reference.call('chacha20_block',[list(range(32)),list(bytes.fromhex('000000090000004a00000000')),1])),expected)
        key=bytes.fromhex('85d6be7857556d337f4452fe42d506a80103808afb0db2fd4abff6af4149f51b')
        self.assertEqual(bytes(reference.call('poly1305',[list(key),list(b'Cryptographic Forum Research Group')])),bytes.fromhex('a8061dc1305136c6c22b8baf0c0127a9'))

    def test_rfc8439_aead_and_tampered_tag(self):
        key=bytes(range(128,160));nonce=bytes.fromhex('070000004041424344454647');aad=bytes.fromhex('50515253c0c1c2c3c4c5c6c7')
        plain=b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it."
        expected=bytes.fromhex('d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d63dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b3692ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc3ff4def08e4b7a9de576d26586cec64b61161ae10b594f09e26a7e902ecbd0600691')
        reference=self.reference();actual=bytes(reference.call('chacha20_poly1305_seal',[list(key),list(nonce),list(aad),list(plain)]));self.assertEqual(actual,expected)
        opened=reference.call('chacha20_poly1305_open',[list(key),list(nonce),list(aad),list(expected)])
        self.assertTrue(opened['ok']);self.assertEqual(bytes(opened['value']),plain)
        damaged=bytearray(expected);damaged[-1]^=1
        rejected=reference.call('chacha20_poly1305_open',[list(key),list(nonce),list(aad),list(damaged)])
        self.assertFalse(rejected['ok']);self.assertEqual(rejected['value'],[])


if __name__=='__main__':unittest.main()
