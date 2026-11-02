#!/usr/bin/env python3
"""X.509 chains as used by today's HTTPS sites, built with OpenSSL, plus the system trust bundle.

Chains: P-384 root -> P-384 intermediate -> P-256 leaf (ecdsa-with-SHA384, Let's Encrypt E5/E6
shape), P-384 root -> P-256 intermediate (GTS WE2 shape), RSA with sha384/sha512WithRSAEncryption,
mixed RSA/EC chains in both directions, P-256 issuers with SHA-384/512, P-384 issuers with
SHA-256, and SHA-1 self-signed trust anchors (accepted as anchors, never as chain signatures).
Each must verify, and tampered signatures/TBS, wrong hostnames, expired or not yet valid
certificates, missing intermediates and impostor roots must be rejected. The TLS 1.3
CertificateVerify helper is checked for P-256/P-384/RSA-PSS leaves.

The system bundle (/etc/ssl/certs/ca-certificates.crt, or $CA_BUNDLE) is parsed PEM -> Base64 ->
DER -> x509_parse, and the number of valid roots is reported; with $X509_BASELINE (or git HEAD)
the previous std:x509 is built too for a before/after count.

  python3 tests/x509_web_language.py [--live] [--require-live]

--live also fetches chains from public HTTPS sites with `openssl s_client` and verifies them
against the parsed system roots; results are printed (and must all verify with --require-live).
"""
import os
from pathlib import Path
import random
import re
import shlex
import subprocess
import sys
import tempfile
import time
from agent_codecs import ROOT, RUNNER, build

MODES = {'sha256WithRSAEncryption': 1, 'ecdsa-with-SHA256': 3, 'ecdsa-with-SHA384': 4, 'sha384WithRSAEncryption': 5,
         'sha512WithRSAEncryption': 6, 'ecdsa-with-SHA512': 7, 'sha1WithRSAEncryption': 8}
LIVE_SITES = ['letsencrypt.org', 'www.google.com', 'github.com', 'www.cloudflare.com', 'en.wikipedia.org', 'www.mozilla.org',
              'www.digicert.com', 'www.sectigo.com', 'www.amazon.com', 'www.apple.com', 'www.microsoft.com', 'www.bbc.co.uk',
              'www.lemonde.fr', 'stackoverflow.com', 'www.python.org', 'go.dev', 'www.rust-lang.org', 'news.ycombinator.com']
REQUIRED_ROOTS = ['ISRG Root X2', 'GTS Root R3', 'GTS Root R4', 'DigiCert Global Root G3']


def openssl(*args, data=None):
    r = subprocess.run(['openssl', *map(str, args)], input=data, capture_output=True, timeout=120)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout


class Pki:
    def __init__(self, root):
        self.root = root; self.serial = 1000

    def key(self, name, kind):
        path = self.root / (name + '.key')
        if kind.startswith('P-'): openssl('genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:' + kind, '-out', path)
        else: openssl('genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:' + kind[3:], '-out', path)
        return path

    def finish(self, name):
        pem = self.root / (name + '.pem'); der = openssl('x509', '-in', pem, '-outform', 'DER')
        (self.root / (name + '.der')).write_bytes(der)
        return der

    def anchor(self, name, kind, digest, subject=None, days=5):
        key = self.key(name, kind)
        openssl('req', '-new', '-x509', '-key', key, '-out', self.root / (name + '.pem'), '-subj', '/CN=' + (subject or name), '-days', days, '-' + digest,
                '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
        return self.finish(name)

    def issue(self, name, kind, issuer, digest, ca=False, host='site.example.test', days=3, subject=None, key_from=None, pathlen=',pathlen:0'):
        key = self.root / (key_from + '.key') if key_from else self.key(name, kind); csr = self.root / (name + '.csr'); self.serial += 1
        openssl('req', '-new', '-key', key, '-out', csr, '-subj', '/CN=' + (subject or (name if ca else host)))
        ext = self.root / (name + '.ext')
        ext.write_text('basicConstraints=critical,CA:TRUE' + pathlen + '\nkeyUsage=critical,keyCertSign,cRLSign\n' if ca else
                       'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:' + host + '\n')
        openssl('x509', '-req', '-in', csr, '-CA', self.root / (issuer + '.pem'), '-CAkey', self.root / (issuer + '.key'), '-set_serial', self.serial,
                '-out', self.root / (name + '.pem'), '-days', days, '-' + digest, '-extfile', ext)
        return self.finish(name)


def frame(cert):
    return len(cert).to_bytes(3, 'big') + cert


def pem_blocks(text):
    return re.findall(r'-----BEGIN CERTIFICATE-----\r?\n.*?-----END CERTIFICATE-----', text, re.S)


def describe(pem):
    text = openssl('x509', '-noout', '-text', '-nameopt', 'oneline', data=pem.encode()).decode(errors='replace')
    subject = re.search(r'Subject: (.*)', text); algorithm = re.search(r'Signature Algorithm: (\S+)', text)
    key = re.search(r'Public Key Algorithm: (\S+)', text); bits = re.search(r'Public-Key: \((\d+) bit\)', text)
    curve = re.search(r'ASN1 OID: (\S+)', text); exponent = re.search(r'Exponent: (\d+)', text)
    cn = re.search(r'CN = ([^,]+)', subject.group(1) if subject else '')
    return dict(subject=(cn.group(1) if cn else subject.group(1) if subject else '?').strip(), signature=algorithm.group(1) if algorithm else '?',
                key=(key.group(1) if key else '?') + (' ' + curve.group(1) if curve and 'ec' in (key.group(1) if key else '').lower() else '') +
                (' ' + bits.group(1) if bits else '') + (' e=' + exponent.group(1) if exponent and exponent.group(1) != '65537' else ''))


def main():
    live = '--live' in sys.argv or '--require-live' in sys.argv; require_live = '--require-live' in sys.argv
    rng = random.Random(509384)
    with tempfile.TemporaryDirectory(prefix='neo-x509-web-') as tmp:
        root = Path(tmp); binary = root / 'x509-web'; bundle_binary = root / 'x509-bundle'
        build('tests/fixtures/x509_web.neo', binary); build('tests/fixtures/x509_bundle.neo', bundle_binary)
        pki = Pki(root)

        # name: (certificates leaf-first, trust anchor, hostname)
        chains = {}
        pki.anchor('x2', 'P-384', 'sha384', 'Test ISRG Root X2'); pki.issue('e5', 'P-384', 'x2', 'sha384', ca=True)
        chains['le-ecdsa'] = (['le-leaf', 'e5'], 'x2'); pki.issue('le-leaf', 'P-256', 'e5', 'sha384')
        pki.anchor('r4', 'P-384', 'sha384', 'Test GTS Root R4'); pki.issue('we2', 'P-256', 'r4', 'sha384', ca=True)
        chains['gts-we2'] = (['gts-leaf', 'we2'], 'r4'); pki.issue('gts-leaf', 'P-256', 'we2', 'sha256')
        pki.anchor('g3', 'P-384', 'sha384', 'Test DigiCert Global Root G3'); pki.issue('g3-ca', 'P-384', 'g3', 'sha384', ca=True)
        chains['p384-leaf'] = (['p384-leaf', 'g3-ca'], 'g3'); pki.issue('p384-leaf', 'P-384', 'g3-ca', 'sha384')
        pki.anchor('rsa-root', 'rsa4096', 'sha384', 'Test RSA Root SHA-384'); pki.issue('rsa-ca', 'rsa2048', 'rsa-root', 'sha384', ca=True)
        chains['rsa-sha384'] = (['rsa-leaf', 'rsa-ca'], 'rsa-root'); pki.issue('rsa-leaf', 'rsa2048', 'rsa-ca', 'sha256')
        pki.anchor('rsa512-root', 'rsa2048', 'sha512', 'Test RSA Root SHA-512'); pki.issue('rsa512-ca', 'rsa3072', 'rsa512-root', 'sha512', ca=True)
        chains['rsa-sha512'] = (['rsa512-leaf', 'rsa512-ca'], 'rsa512-root'); pki.issue('rsa512-leaf', 'rsa2048', 'rsa512-ca', 'sha512')
        pki.issue('rsa-ec-ca', 'P-384', 'rsa-root', 'sha384', ca=True)
        chains['rsa-to-ec'] = (['rsa-ec-leaf', 'rsa-ec-ca'], 'rsa-root'); pki.issue('rsa-ec-leaf', 'P-256', 'rsa-ec-ca', 'sha384')
        pki.issue('ec-rsa-ca', 'rsa2048', 'x2', 'sha384', ca=True)
        chains['ec-to-rsa'] = (['ec-rsa-leaf', 'ec-rsa-ca'], 'x2'); pki.issue('ec-rsa-leaf', 'rsa2048', 'ec-rsa-ca', 'sha384')
        pki.anchor('p256-root', 'P-256', 'sha384', 'Test P-256 Root SHA-384')
        chains['p256-sha384'] = (['p256-leaf'], 'p256-root'); pki.issue('p256-leaf', 'P-256', 'p256-root', 'sha384')
        chains['p256-sha512'] = (['p256-leaf512'], 'p256-root'); pki.issue('p256-leaf512', 'P-256', 'p256-root', 'sha512')
        pki.anchor('p384-root', 'P-384', 'sha256', 'Test P-384 Root SHA-256')
        chains['p384-sha256'] = (['p384-leaf256'], 'p384-root'); pki.issue('p384-leaf256', 'P-256', 'p384-root', 'sha256')
        chains['p384-sha512'] = (['p384-leaf512'], 'x2'); pki.issue('p384-leaf512', 'P-384', 'x2', 'sha512')
        pki.anchor('sha1-root', 'rsa2048', 'sha1', 'Test Legacy SHA-1 Root')
        chains['sha1-anchor'] = (['sha1-anchored'], 'sha1-root'); pki.issue('sha1-anchored', 'rsa2048', 'sha1-root', 'sha256')
        pki.issue('sha1-signed', 'rsa2048', 'sha1-root', 'sha1')  # SHA-1 chain signature: must be rejected
        pki.issue('short-ca', 'P-384', 'x2', 'sha384', ca=True, days=1); pki.issue('short-leaf', 'P-256', 'short-ca', 'sha384', days=4)
        pki.anchor('x2-impostor', 'P-384', 'sha384', 'Test ISRG Root X2')  # same subject, different key
        # Google Trust Services shape: the server also sends GTS Root R4 cross-signed by an RSA
        # "GlobalSign Root CA" that is no longer in the trust store; WE2 is issued by the trusted R4.
        pki.anchor('globalsign', 'rsa2048', 'sha256', 'Test GlobalSign Root CA')
        pki.issue('r4-cross', 'P-384', 'globalsign', 'sha256', ca=True, subject='Test GTS Root R4', key_from='r4', pathlen='')
        now = int(time.time()) + 60
        der = {path.stem: path.read_bytes() for path in root.glob('*.der')}

        def verify(chain, anchors, host='site.example.test', timestamp=now):
            payload = bytes([len(host)]) + host.encode() + timestamp.to_bytes(8, 'big') + bytes([len(chain), len(anchors)]) + b''.join(frame(c) for c in chain + anchors)
            r = subprocess.run(RUNNER + [str(binary), '0', '0'], input=payload, capture_output=True, timeout=60)
            assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
            return r.stdout == b'verified\n'

        # Every generated certificate parses with the expected signature mode and key.
        pem_text = ''.join((root / (name + '.pem')).read_text() for name in sorted(der))
        lines = subprocess.run(RUNNER + [str(bundle_binary)], input=pem_text.encode(), capture_output=True, timeout=60, check=True).stdout.decode().splitlines()
        for name, line in zip(sorted(der), lines):
            valid, mode, ec, rsa, size = line.split(); info = describe((root / (name + '.pem')).read_text())
            assert valid == '1' and int(mode) == MODES[info['signature']], (name, line, info)
            assert int(ec) == (97 if 'secp384r1' in info['key'] else 65 if 'prime256v1' in info['key'] else 0) and (rsa == '1') == ('rsa' in info['key'].lower()), (name, line, info)
        print(f'PASS {len(der)} generated certificates parse with the expected signature mode and key type (P-256, P-384, RSA 2048/3072/4096)', flush=True)

        rejected = 0
        for name, (names, anchor) in chains.items():
            chain = [der[n] for n in names]; anchors = [der[anchor]]
            assert verify(chain, anchors), name
            checks = [verify(chain, anchors, 'other.example.test'), verify(chain, anchors, timestamp=now + 86400 * 30), verify(chain, anchors, timestamp=now - 86400 * 2),
                      verify(chain[:-1], anchors) if len(chain) > 1 else verify(chain, [der['x2-impostor' if anchor != 'x2' else 'r4']])]
            for index in range(len(chain)):
                tampered = list(chain); tampered[index] = tampered[index][:-1] + bytes([tampered[index][-1] ^ 1]); checks.append(verify(tampered, anchors))
                for at in (30, len(chain[index]) // 2):
                    body = bytearray(chain[index]); body[at] ^= 1; tampered = list(chain); tampered[index] = bytes(body); checks.append(verify(tampered, anchors))
            assert not any(checks), (name, checks); rejected += len(checks)
        assert not verify([der['le-leaf'], der['e5']], [der['x2-impostor']]), 'impostor root accepted'
        assert not verify([der['sha1-signed']], [der['sha1-root']]), 'SHA-1 chain signature accepted'
        assert verify([der['short-leaf'], der['short-ca']], [der['x2']]) and not verify([der['short-leaf'], der['short-ca']], [der['x2']], timestamp=now + 86400 * 2)
        assert not verify([der['le-leaf'], der['e5']], [der['r4']]) and not verify([der['gts-leaf'], der['we2']], [der['x2']])
        served = [der['gts-leaf'], der['we2'], der['r4-cross']]
        assert verify(served, [der['r4']]), 'chain ending in a cross-sign towards an untrusted root'
        assert verify(served, [der['globalsign']]), 'chain through the cross-sign'
        assert verify([der['le-leaf'], der['e5'], der['x2']], [der['x2']]), 'served trust anchor'
        tampered_we2 = der['we2'][:-1] + bytes([der['we2'][-1] ^ 1])
        assert not verify([der['gts-leaf'], tampered_we2, der['r4-cross']], [der['r4']]) and not verify([der['gts-leaf'], der['r4-cross']], [der['r4']])
        assert not verify(served, [der['x2']]) and not verify(served, [der['r4']], timestamp=now + 86400 * 30)
        rejected += 10
        for _ in range(60):
            mutated = bytearray(der['le-leaf']); at = rng.randrange(len(mutated)); mutated[at] ^= 1 << rng.randrange(8)
            assert not verify([bytes(mutated), der['e5']], [der['x2']]), at
        print(f'PASS X.509 chains: {len(chains)} shapes verify ({", ".join(chains)}); {rejected + 60} rejections incl. wrong host, expiry, '
              'not-yet-valid, missing intermediate, impostor root, SHA-1 chain signature, tampered signatures/TBS and 60 random bit flips', flush=True)

        # TLS 1.3 CertificateVerify by the leaf key.
        def tls_signature(leaf, scheme, message, signature):
            payload = scheme.to_bytes(2, 'big') + frame(der[leaf]) + len(signature).to_bytes(2, 'big') + signature + message
            r = subprocess.run(RUNNER + [str(binary), '2', '0'], input=payload, capture_output=True, timeout=60)
            assert r.returncode == 0, r.stderr
            return r.stdout == b'yes\n'
        content = b' ' * 64 + b'TLS 1.3, server CertificateVerify\0' + rng.randbytes(48); (root / 'content').write_bytes(content)
        tls_cases = 0
        for leaf, digest, scheme, options in [('p384-leaf', 'sha384', 1283, []), ('le-leaf', 'sha256', 1027, []),
                                              ('rsa-leaf', 'sha256', 2052, ['-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:32']),
                                              ('rsa-leaf', 'sha384', 2053, ['-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:48'])]:
            signature = openssl('dgst', '-' + digest, '-sign', root / (leaf + '.key'), *options, root / 'content')
            assert tls_signature(leaf, scheme, content, signature), (leaf, scheme)
            assert not tls_signature(leaf, scheme, content + b'x', signature) and not tls_signature(leaf, scheme, content, signature[:-1] + bytes([signature[-1] ^ 1]))
            others = [s for s in (1027, 1283, 2052, 2053, 1025, 2055) if s != scheme]
            assert not any(tls_signature(leaf, other, content, signature) for other in others), (leaf, scheme)
            tls_cases += 3 + len(others)
        pkcs1 = openssl('dgst', '-sha384', '-sign', root / 'rsa-leaf.key', root / 'content'); assert not tls_signature('rsa-leaf', 2053, content, pkcs1)
        print(f'PASS TLS 1.3 CertificateVerify helper: ecdsa_secp384r1_sha384 with a P-384 leaf, P-256, RSA-PSS SHA-256/384; {tls_cases + 1} cases incl. scheme/curve mismatches', flush=True)

        start = time.monotonic(); repeat = 20
        payload = bytes([17]) + b'site.example.test' + now.to_bytes(8, 'big') + bytes([2, 1]) + b''.join(frame(c) for c in (der['le-leaf'], der['e5'], der['x2']))
        r = subprocess.run(RUNNER + [str(binary), '3', str(repeat)], input=payload, capture_output=True, timeout=600)
        assert r.returncode == 0 and r.stdout == b'verified %d\n' % repeat, r.stdout
        print(f'TIME Let\'s Encrypt ECDSA shape (two P-384/SHA-384 signatures + parsing): {(time.monotonic() - start) / repeat * 1000:.1f} ms per x509_verify', flush=True)

        # System trust bundle.
        bundle_path = Path(os.environ.get('CA_BUNDLE', '/etc/ssl/certs/ca-certificates.crt'))
        if not bundle_path.exists():
            print(f'SKIP system bundle: {bundle_path} not found', flush=True); return
        bundle = bundle_path.read_text(errors='replace'); blocks = pem_blocks(bundle)

        def parse_bundle(executable):
            out = subprocess.run(RUNNER + [str(executable)], input=bundle.encode(), capture_output=True, timeout=300, check=True).stdout.decode().splitlines()
            total, valid = re.match(r'total (\d+) valid (\d+)', out[-1]).groups()
            assert int(total) == len(blocks), (total, len(blocks))
            return [line.split()[0] == '1' for line in out[:-1]], int(valid)
        after, after_count = parse_bundle(bundle_binary)
        baseline = os.environ.get('X509_BASELINE'); old_source = None
        if baseline and Path(baseline).exists(): old_source = Path(baseline).read_text()
        else:
            g = subprocess.run(['git', 'show', 'HEAD:stdlib/x509.neo'], cwd=ROOT, capture_output=True, text=True)
            if g.returncode == 0 and g.stdout != (ROOT / 'stdlib/x509.neo').read_text(): old_source = g.stdout
        infos = [describe(block) for block in blocks]
        if old_source:
            (root / 'x509_before.neo').write_text(old_source)
            (root / 'bundle_before.neo').write_text((ROOT / 'tests/fixtures/x509_bundle.neo').read_text().replace('import "std:x509"', 'import "x509_before.neo"'))
            before_binary = root / 'bundle-before'; build(str(root / 'bundle_before.neo'), before_binary)
            before, before_count = parse_bundle(before_binary)
            lost = [infos[i]['subject'] for i in range(len(blocks)) if before[i] and not after[i]]
            assert not lost, ('roots no longer parse', lost)
            gained = {}
            for i in range(len(blocks)):
                if after[i] and not before[i]: gained.setdefault(infos[i]['key'] + ' / ' + infos[i]['signature'], []).append(infos[i]['subject'])
            print(f'PASS system bundle {bundle_path}: {before_count} of {len(blocks)} roots parsed valid before, {after_count} after (+{after_count - before_count}, none lost)', flush=True)
            for kind, names in sorted(gained.items()): print(f'  gained {len(names):3d} {kind}: {", ".join(names[:4])}{" ..." if len(names) > 4 else ""}', flush=True)
        else:
            print(f'PASS system bundle {bundle_path}: {after_count} of {len(blocks)} roots parse valid (no baseline std:x509 available)', flush=True)
        for i in range(len(blocks)):
            if not after[i]: print(f'  still invalid: {infos[i]["subject"]} ({infos[i]["key"]}, {infos[i]["signature"]})', flush=True)
        for name in REQUIRED_ROOTS:
            present = [i for i in range(len(blocks)) if infos[i]['subject'] == name]
            assert all(after[i] for i in present), (name, 'does not parse')
            print(f'  {name}: {"parses valid" if present else "not in bundle"}', flush=True)

        if not live: return
        verified = 0; attempts = 0
        for site in LIVE_SITES:
            for label, sigalgs in (('ECDSA', 'ecdsa_secp256r1_sha256:ecdsa_secp384r1_sha384'), ('RSA', 'rsa_pss_rsae_sha256:rsa_pss_rsae_sha384:rsa_pkcs1_sha256')):
                try:
                    r = subprocess.run(['openssl', 's_client', '-connect', site + ':443', '-servername', site, '-showcerts', '-sigalgs', sigalgs],
                                       input=b'', capture_output=True, timeout=20)
                except subprocess.TimeoutExpired:
                    print(f'LIVE {site} {label}: timeout', flush=True); continue
                served = pem_blocks(r.stdout.decode(errors='replace'))
                if not served:
                    print(f'LIVE {site} {label}: no chain ({r.stderr.decode(errors="replace").strip().splitlines()[-1:] or "?"})', flush=True); continue
                chain = [openssl('x509', '-outform', 'DER', data=block.encode()) for block in served]
                shape = ' <- '.join(f'{d["key"].replace("id-ecPublicKey ", "")}/{d["signature"]}' for d in (describe(block) for block in served))
                payload = bytes([len(site)]) + site.encode() + int(time.time()).to_bytes(8, 'big') + bytes([len(chain)]) + b''.join(frame(c) for c in chain) + bundle.encode()
                result = subprocess.run(RUNNER + [str(binary), '1', '0'], input=payload, capture_output=True, timeout=120)
                attempts += 1; ok = result.stdout.startswith(b'verified'); verified += ok
                print(f'LIVE {site} {label}: {result.stdout.decode().strip()} [{shape}]', flush=True)
        print(f'LIVE summary: {verified} of {attempts} served chains verified against the system roots', flush=True)
        if require_live: assert attempts and verified == attempts


if __name__ == '__main__':
    main()
