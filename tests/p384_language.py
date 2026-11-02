#!/usr/bin/env python3
"""Native P-384 (and generic P-256) ECDSA verification vs Python integers and standard Go crypto/ecdsa.

1. Montgomery field/order arithmetic of std:p384 for both curves against Python integers.
2. Public-key validation against Go (off-curve points, coordinates >= p, wrong encodings).
3. Differential ECDSA verification: Go signs with SHA-256/384/512 or raw digests; every
   valid, mutated, wrong-key, high-s, out-of-range and malformed DER case is verified by
   both Go and Neo and the answers must agree.
4. Per-operation timing of a P-384 verification.
"""
import json
import os
import random
import subprocess
import tempfile
import time
from pathlib import Path
from agent_codecs import ROOT, RUNNER, build

CURVES = {
    384: dict(p=2**384 - 2**128 - 2**96 + 2**32 - 1,
              n=0xffffffffffffffffffffffffffffffffffffffffffffffffc7634d81f4372ddf581a0db248b0a77aecec196accc52973,
              b=0xb3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875ac656398d8a2ed19d2a85c8edd3ec2aef, size=48, code=1),
    256: dict(p=2**256 - 2**224 + 2**192 + 2**96 - 1,
              n=0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551,
              b=0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b, size=32, code=0),
}
HASHES = {0: 'digest', 1: 'sha256', 2: 'sha384', 3: 'sha512'}

FIELD_MAIN = '''
import "std:io"
type FieldBatch = { at:i64,out:Arr u8 _ }
fn field_step(move state:FieldBatch,input:Arr u8 n) -> FieldBatch
  = let at=state.at in let curve=if str_byte(input,at)==1 then ecw_p384() else ecw_p256() in
    let mod=if str_byte(input,at+1)==1 then curve.order else curve.field in let op=str_byte(input,at+2) in
    let size=curve.size in let count=len(mod.modulus) in check count>=1 && count<=32 in
    let a=ecw_mul(ecw_limbs(str_slice(input,at+3,at+3+size),count),mod.r2,mod) in
    let b=ecw_mul(ecw_limbs(str_slice(input,at+3+size,at+3+2*size),count),mod.r2,mod) in
    let result=if op==0 then ecw_mul(a,b,mod) else if op==1 then ecw_add(a,b,mod.modulus) else if op==2 then ecw_sub(a,b,mod.modulus) else
      if op==3 then ecw_inverse(a,mod) else a in
    FieldBatch { at=at+3+2*size,out=concat(state.out,ecw_bytes(ecw_mul(result,arr(i in 0..count) if i==0 then 1 else 0,mod),size)) }
effect(fs,process) fn main() -> unit
  = let raw=file_read(0,4194304) in check raw.ok in let input=raw.value in
    let batch=loop(state=FieldBatch { at=0,out="" }) while state.at<len(input) next(field_step(state,input)) yield state in
    let output=file_write(1,batch.out) in check output.ok in noop()
'''


def integer(x, pad=0):
    """DER INTEGER; pad adds non-minimal leading zero bytes (invalid DER)."""
    b = x.to_bytes(max(1, (x.bit_length() + 7) // 8), 'big')
    if b[0] & 128: b = b'\0' + b
    b = b'\0' * pad + b
    return b'\x02' + bytes([len(b)]) + b


def der(r, s, pad_r=0):
    body = integer(r, pad_r) + integer(s)
    return b'\x30' + bytes([len(body)]) + body


def parse(sig):
    assert sig[0] == 0x30 and sig[1] == len(sig) - 2
    lr = sig[3]; r = int.from_bytes(sig[4:4 + lr], 'big'); ls = sig[5 + lr]; s = int.from_bytes(sig[6 + lr:6 + lr + ls], 'big')
    return r, s


def point(bits, x, y, prefix=4):
    size = CURVES[bits]['size']
    return bytes([prefix]) + x.to_bytes(size, 'big') + y.to_bytes(size, 'big')


def main():
    rng = random.Random(384256)
    with tempfile.TemporaryDirectory(prefix='neo-p384-') as tmp:
        root = Path(tmp)
        source = root / 'field.neo'; source.write_text((ROOT / 'stdlib/p384.neo').read_text() + FIELD_MAIN)
        field = root / 'field'; build(str(source), field)
        verifier = root / 'p384'; build('tests/fixtures/language_p384.neo', verifier)
        oracle = root / 'oracle'
        subprocess.run(['go', 'build', '-trimpath', '-o', str(oracle), 'tests/p384_oracle.go'], cwd=ROOT,
                       env={**os.environ, 'GOWORK': 'off', 'CGO_ENABLED': '0'}, capture_output=True, check=True)

        # 1. Field and order arithmetic.
        records = []; expected = []
        for bits, c in CURVES.items():
            size = c['size']
            for order, m in ((0, c['p']), (1, c['n'])):
                pairs = [(0, 0), (1, 1), (m - 1, m - 1), (m - 2, 2), (2**(bits - 1), m - 1)] + [(rng.randrange(m), rng.randrange(m)) for _ in range(60)]
                for index, (a, b) in enumerate(pairs):
                    ops = [(0, a * b % m), (1, (a + b) % m), (2, (a - b) % m)] + ([(3, pow(a, -1, m))] if a and index < 20 else [])
                    for op, value in ops:
                        records.append(bytes([c['code'], order, op]) + a.to_bytes(size, 'big') + b.to_bytes(size, 'big')); expected.append(value.to_bytes(size, 'big'))
                for a in (m, m + 1, 2**bits - 1, rng.randrange(m, 2**bits)):
                    records.append(bytes([c['code'], order, 4]) + a.to_bytes(size, 'big') + bytes(size)); expected.append((a % m).to_bytes(size, 'big'))
        p = subprocess.run(RUNNER + [str(field)], input=b''.join(records), capture_output=True, timeout=300)
        assert p.returncode == 0, p.stderr
        assert p.stdout == b''.join(expected), 'field arithmetic mismatch'
        print(f'PASS P-384/P-256 30-bit-limb Montgomery field and order arithmetic: {len(records)} mul/add/sub/inverse/reduction cases vs Python integers', flush=True)

        def go(cases):
            r = subprocess.run([str(oracle)], input=''.join(json.dumps(case) + '\n' for case in cases), capture_output=True, text=True, timeout=300)
            assert r.returncode == 0, r.stderr
            return [bytes.fromhex(json.loads(line)) for line in r.stdout.splitlines()]

        def neo(mode, data, repeat=0):
            r = subprocess.run(RUNNER + [str(verifier), str(mode), str(repeat)], input=data, capture_output=True, timeout=600)
            assert r.returncode == 0, (mode, r.returncode, r.stderr)
            return r.stdout

        # 2. Public keys.
        keys = {}
        for bits in CURVES:
            generated = go([dict(Mode=0, Curve=bits)] * 10)
            n = CURVES[bits]['n']; size = CURVES[bits]['size']
            special = [d.to_bytes(size, 'big') for d in (1, 2, 3, n - 1, n - 2)]
            publics = go([dict(Mode=4, Curve=bits, Key=d.hex()) for d in special])
            keys[bits] = [(g[:size], g[size:]) for g in generated] + list(zip(special, publics))
        bad_keys = []
        for bits, c in CURVES.items():
            p_, size = c['p'], c['size']
            for _, public in keys[bits][:4]:
                x = int.from_bytes(public[1:1 + size], 'big'); y = int.from_bytes(public[1 + size:], 'big')
                bad_keys += [(bits, point(bits, x, (y + 1) % p_)), (bits, point(bits, (x + 1) % p_, y)), (bits, point(bits, x, p_ - y)),
                             (bits, public[:-1]), (bits, public + b'\0'), (bits, b'\x02' + public[1:]), (bits, b'\x03' + public[1:1 + size]),
                             (bits, point(bits, x, y + p_) if y + p_ < 2**(8 * size) else point(bits, x, 2**(8 * size) - 1)),
                             (bits, point(bits, x + p_, y) if x + p_ < 2**(8 * size) else point(bits, 2**(8 * size) - 1, y))]
            bad_keys += [(bits, point(bits, 0, 0)), (bits, b'\0'), (bits, b''), (bits, point(bits, p_, 0)), (bits, bytes([4]) + bytes([255]) * (2 * size)),
                         (bits, point(bits, rng.randrange(p_), rng.randrange(p_)))]
        bad_keys += [(384, keys[256][0][1]), (256, keys[384][0][1])]
        key_cases = [(bits, public) for bits in CURVES for _, public in keys[bits]] + bad_keys
        answers = neo(1, b''.join(bytes([CURVES[bits]['code'], len(pub)]) + pub for bits, pub in key_cases))
        reference = go([dict(Mode=3, Curve=bits, Public=pub.hex()) for bits, pub in key_cases])
        assert len(answers) == len(key_cases)
        for (bits, pub), mine, theirs in zip(key_cases, answers, reference):
            assert (mine == ord('1')) == (theirs == b'yes'), (bits, pub.hex(), chr(mine), theirs)
        good = sum(len(v) for v in keys.values())
        assert all(a == ord('1') for a in answers[:good])
        negated = sum(1 for a in answers[good:] if a == ord('1'))  # (x, p-y) = -P is a valid point
        print(f'PASS public keys: {good} generated/special keys and {negated} negated points valid; {len(bad_keys) - negated} off-curve, '
              'out-of-range and malformed encodings rejected, all in agreement with Go', flush=True)

        # 3. Differential ECDSA verification.
        cases = []  # (bits, hash, public, message, signature, expected or None)
        sign_requests = []
        for bits in CURVES:
            for i, (secret, public) in enumerate(keys[bits]):
                for hash_mode in (1, 2, 3, 0):
                    if bits == 256 and hash_mode == 1 and i > 3: continue
                    message = rng.randbytes([0, 1, 47, 48, 49, 64, 111, 128, 129, 1000][(i + hash_mode) % 10]) if hash_mode else rng.randbytes([20, 28, 32, 48, 64][i % 5])
                    sign_requests.append((bits, hash_mode, secret, public, message))
        signatures = go([dict(Mode=1, Curve=bits, Hash=h, Key=secret.hex(), Data=message.hex()) for bits, h, secret, public, message in sign_requests])
        for (bits, h, secret, public, message), sig in zip(sign_requests, signatures):
            n = CURVES[bits]['n']; r, s = parse(sig)
            cases.append((bits, h, public, message, sig, True))
            cases.append((bits, h, public, message, der(r, n - s), True))  # high-s is valid ECDSA
            mutated = bytearray(sig); at = rng.randrange(len(sig)); mutated[at] ^= 1 << rng.randrange(8); cases.append((bits, h, public, message, bytes(mutated), None))
            cases.append((bits, h, public, message + b'!' if h else bytes([message[0] ^ 1]) + message[1:], sig, False))
            other = keys[bits][(keys[bits].index((secret, public)) + 1) % len(keys[bits])][1]
            cases.append((bits, h, other, message, sig, False))
            for bad in (der(0, s), der(r, 0), der(n, s), der(r, n), der(r + n, s) if r + n < 2**(8 * CURVES[bits]['size']) else der(2**(8 * CURVES[bits]['size']) - 1, s),
                        der(r, s, pad_r=1), sig + b'\0', sig[:-1], b'\x30\x81' + bytes([len(sig) - 2]) + sig[2:], b'\x30' + bytes([3 + len(integer(s))]) + b'\x02\x01\xff' + integer(s)):
                cases.append((bits, h, public, message, bad, False))
        # ecdsa-with-SHA384 under a P-256 key and P-384 with a SHA-256 digest go through the same path; std:p256 cross-check:
        for i, (secret, public) in enumerate(keys[256][:4]):
            message = rng.randbytes(77); sig = go([dict(Mode=1, Curve=256, Hash=1, Key=secret.hex(), Data=message.hex())])[0]
            cases.append(('std256', 1, public, message, sig, True)); cases.append(('std256', 1, public, message + b'?', sig, False))
        records = []; requests = []
        for bits, h, public, message, sig, _ in cases:
            code = 2 if bits == 'std256' else CURVES[bits]['code']
            records.append(bytes([code, h, len(public)]) + public + bytes([len(sig)]) + sig + len(message).to_bytes(2, 'big') + message)
            requests.append(dict(Mode=2, Curve=256 if bits == 'std256' else bits, Hash=h, Public=public.hex(), Data=message.hex(), Signature=sig.hex()))
        start = time.monotonic(); answers = neo(0, b''.join(records)); elapsed = time.monotonic() - start
        reference = go(requests)
        assert len(answers) == len(cases), (len(answers), len(cases))
        counts = {True: 0, False: 0}
        for case, mine, theirs in zip(cases, answers, reference):
            bits, h, public, message, sig, want = case
            accepted = mine == ord('1')
            assert accepted == (theirs == b'yes'), ('disagree with Go', bits, HASHES[h], public.hex(), message.hex(), sig.hex(), chr(mine), theirs)
            if want is not None: assert accepted == want, ('unexpected', bits, HASHES[h], sig.hex(), accepted)
            counts[accepted] += 1
        per_curve = {b: sum(1 for c in cases if c[0] == b) for b in (384, 256, 'std256')}
        print(f'PASS ECDSA differential vs Go crypto/ecdsa: {len(cases)} verifications (P-384 {per_curve[384]}, P-256 generic {per_curve[256]}, std:p256 {per_curve["std256"]}); '
              f'{counts[True]} accepted, {counts[False]} rejected incl. bit flips, wrong keys/messages, high-s, r/s out of range and malformed DER; batch {elapsed:.2f}s', flush=True)

        # 4. Timing: one valid P-384/SHA-384 verification repeated (odd runs alter the message and fail at the final comparison).
        def timing(bits, h, code):
            secret, public = keys[bits][0]; message = rng.randbytes(256)
            sig = go([dict(Mode=1, Curve=bits, Hash=h, Key=secret.hex(), Data=message.hex())])[0]
            record = bytes([code, h, len(public)]) + public + bytes([len(sig)]) + sig + len(message).to_bytes(2, 'big') + message
            results = {}
            for repeat in (2, 42):
                best = None
                for _ in range(3):
                    start = time.monotonic(); out = neo(2, record, repeat); spent = time.monotonic() - start
                    assert out == f'valid={repeat // 2}\n'.encode(), out
                    best = spent if best is None else min(best, spent)
                results[repeat] = best
            return (results[42] - results[2]) / 40 * 1000
        for label, bits, h, code in (('P-384 SHA-384', 384, 2, 1), ('P-384 SHA-256', 384, 1, 1), ('P-256 SHA-384 (std:p384 path)', 256, 2, 0), ('P-256 SHA-256 (std:p256)', 256, 1, 2)):
            print(f'TIME {label} verify: {timing(bits, h, code):.2f} ms/op', flush=True)


if __name__ == '__main__':
    main()
