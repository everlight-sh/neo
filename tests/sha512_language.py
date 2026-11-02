#!/usr/bin/env python3
"""Native SHA-512/SHA-384 and HMAC against FIPS 180-4 / RFC 4231 vectors and hashlib."""
import hashlib
import hmac
import random
import subprocess
import tempfile
from pathlib import Path
from agent_codecs import RUNNER, build

# FIPS 180-4 examples (NIST CSRC "SHA_All" example values).
TWO_BLOCK = b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu'
NIST = [
    (b'abc', 'ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f',
     'cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7'),
    (b'', 'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e',
     '38b060a751ac96384cd9327eb1b1e36a21fdb71114be07434c0cc7bf63f6e1da274edebfe76f65fbd51ad2f14898b95b'),
    (TWO_BLOCK, '8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909',
     '09330c33f71147e83d192fc782cd1b4753111b173b3b05d22fa08086e3b0f712fcc7c71a557e2db966c3e9fa91746039'),
    (b'a' * 1000000, 'e718483d0ce769644e2e42c7bc15b4638e1f98b13b2044285632a803afa973ebde0ff244877ea60a4cb0432ce577c31beb009c5c2c49aa2e4eadb217ad8cc09b',
     '9d0e1809716474cb086e834e310a4a1ced149e9c00f248527972cec5704c2a5b07b8b3dc38ecc4ebae97ddd87f3d8985'),
]
# RFC 4231 test cases 1, 2, 3, 4, 6 and 7 (HMAC-SHA-384, HMAC-SHA-512).
RFC4231 = [
    (b'\x0b' * 20, b'Hi There',
     'afd03944d84895626b0825f4ab46907f15f9dadbe4101ec682aa034c7cebc59cfaea9ea9076ede7f4af152e8b2fa9cb6',
     '87aa7cdea5ef619d4ff0b4241a1d6cb02379f4e2ce4ec2787ad0b30545e17cdedaa833b7d6b8a702038b274eaea3f4e4be9d914eeb61f1702e696c203a126854'),
    (b'Jefe', b'what do ya want for nothing?',
     'af45d2e376484031617f78d2b58a6b1b9c7ef464f5a01b47e42ec3736322445e8e2240ca5e69e2c78b3239ecfab21649',
     '164b7a7bfcf819e2e395fbe73b56e0a387bd64222e831fd610270cd7ea2505549758bf75c05a994a6d034f65f8f0e6fdcaeab1a34d4a6b4b636e070a38bce737'),
    (b'\xaa' * 20, b'\xdd' * 50,
     '88062608d3e6ad8a0aa2ace014c8a86f0aa635d947ac9febe83ef4e55966144b2a5ab39dc13814b94e3ab6e101a34f27',
     'fa73b0089d56a284efb0f0756c890be9b1b5dbdd8ee81a3655f83e33b2279d39bf3e848279a722c806b485a47e67c807b946a337bee8942674278859e13292fb'),
    (bytes(range(1, 26)), b'\xcd' * 50,
     '3e8a69b7783c25851933ab6290af6ca77a9981480850009cc5577c6e1f573b4e6801dd23c4a7d679ccf8a386c674cffb',
     'b0ba465637458c6990e5a8c5f61d4af7e576d97ff94b872de76f8050361ee3dba91ca5c11aa25eb4d679275cc5788063a5f19741120c4f2de2adebeb10a298dd'),
    (b'\xaa' * 131, b'Test Using Larger Than Block-Size Key - Hash Key First',
     '4ece084485813e9088d2c63a041bc5b44f9ef1012a2b588f3cd11f05033ac4c60c2ef6ab4030fe8296248df163f44952',
     '80b24263c7c1a3ebb71493c1dd7be8b49b46d1f41b4aeec1121b013783f8f3526b56d037e05f2598bd0fd2215d6a1e5295e64f73f63f0aec8b915a985d786598'),
    (b'\xaa' * 131, b'This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm.',
     '6617178e941f020d351e2f254e8fd32c602420feb0b8fb9adccebb82461e99c5a678cc31e799176d3860e6110c46523e',
     'e37b6a775dc87dbaa4dfa9f96e5e3ffddebd71f8867289865df5a32d20cdc944b6022cac3c4982b10d5eeb55c3e4de15134676fb6de0446065c97440fa8c6a58'),
]


def main():
    rng = random.Random(51280384)
    with tempfile.TemporaryDirectory(prefix='neo-sha512-') as tmp:
        binary = Path(tmp) / 'sha512'; build('tests/fixtures/language_sha512.neo', binary)

        def run(mode, data):
            p = subprocess.run(RUNNER + [str(binary), str(mode)], input=data, capture_output=True, timeout=120)
            assert p.returncode == 0, (mode, p.returncode, p.stderr)
            return p.stdout

        for message, d512, d384 in NIST:
            assert run(0, message).hex() == d512 == hashlib.sha512(message).hexdigest(), len(message)
            assert run(1, message).hex() == d384 == hashlib.sha384(message).hexdigest(), len(message)
        print(f'PASS SHA-512/SHA-384 FIPS 180-4 vectors: {len(NIST)} messages incl. two-block and one million bytes', flush=True)

        sizes = list(range(0, 300)) + [383, 384, 385, 511, 512, 513, 1023, 1024, 1025, 4095, 4096, 4097, 65535, 65536, 65537]
        sizes += [rng.randrange(300, 20000) for _ in range(40)]
        messages = [rng.randbytes(size) for size in sizes]
        out = run(4, b''.join(len(m).to_bytes(4, 'big') + m for m in messages))
        assert len(out) == 112 * len(messages), len(out)
        for i, m in enumerate(messages):
            chunk = out[i * 112:(i + 1) * 112]
            assert chunk[:64] == hashlib.sha512(m).digest(), ('sha512', len(m))
            assert chunk[64:] == hashlib.sha384(m).digest(), ('sha384', len(m))
        for size in (111, 112, 127, 128, 129, 239, 240, 255, 256, 257, 1048576):
            m = rng.randbytes(size)
            assert run(0, m) == hashlib.sha512(m).digest() and run(1, m) == hashlib.sha384(m).digest(), size
        print(f'PASS SHA-512/SHA-384 against hashlib: every length 0..299, block/padding boundaries and random lengths ({len(messages) + 11} messages, up to 1 MiB)', flush=True)

        def mac(mode, key, message):
            return run(mode, len(key).to_bytes(2, 'big') + key + message)

        for key, message, h384, h512 in RFC4231:
            assert mac(3, key, message).hex() == h384 == hmac.digest(key, message, 'sha384').hex(), len(key)
            assert mac(2, key, message).hex() == h512 == hmac.digest(key, message, 'sha512').hex(), len(key)
        count = 0
        for key_size in (0, 1, 48, 64, 127, 128, 129, 200):
            for size in (0, 1, 111, 112, 128, 129, 1000):
                key = rng.randbytes(key_size); message = rng.randbytes(size); count += 1
                assert mac(3, key, message) == hmac.digest(key, message, 'sha384'), (key_size, size)
                assert mac(2, key, message) == hmac.digest(key, message, 'sha512'), (key_size, size)
        print(f'PASS HMAC-SHA-384/512: {len(RFC4231)} RFC 4231 vectors and {count} key/message size pairs against Python hmac', flush=True)


if __name__ == '__main__':
    main()
