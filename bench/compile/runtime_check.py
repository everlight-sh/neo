#!/usr/bin/env python3
"""Run time of the programs whose code the inline expansion cap changes, before and after.

usage: runtime_check.py OUT.json ROUNDS     (NEO_TREES as for run.py)

NEO_DEV lists labels whose builds use --dev; one tree under two labels
(NEO_TREES=release=DIR,dev=DIR NEO_DEV=dev) compares the two profiles.

The cap leaves most programs' IR byte-identical; these are the ones it
changes that do measurable work, followed by orders_json, library_bench and
the compute kernels (mandel, stencil, nbody, sieve), which a lower cap could
reach:
  orders_stages  bench/core/orders_stages.neo, modes 2 (four json_get lookups
                 per order) and 3 (lookups plus reads), 1,000 orders x 1,000.
  json-cli       examples/json-cli filtering and sorting 200,000 records.
  https          bench/fetch/fetch.neo against bench/fetch's Go server: 300
                 requests on new connections (a TLS 1.3 handshake each, P-256
                 certificate) and 50 x 1 MiB over one kept-alive connection.
  p384           tests/fixtures/language_p384.neo verifying one P-384/SHA-384
                 signature (made with openssl) 200 times; odd runs alter the
                 message, as in tests/p384_language.py.
  library_bench  examples/library_bench.neo, modes 0 (parse a small JSON
                 document, three lookups) and 1 (text, vector and map helpers),
                 1,000,000 iterations each.
Each round runs every tree once per case, alternating which tree goes first.
Outputs must match between trees. Clients and the server share CPU 0, as in
bench/fetch. REUSE_BUILDS=1 keeps binaries a previous run built.
"""
import hashlib, importlib.util, json, os, random, socket, statistics, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import TREES, WORK  # noqa: E402

FETCH = Path(__file__).resolve().parents[1] / 'fetch'
spec = importlib.util.spec_from_file_location('fetch_run', FETCH / 'run.py')
fetch = importlib.util.module_from_spec(spec); spec.loader.exec_module(fetch)  # certificates, free_port

OUT = WORK / 'runtime'
# Compute kernels at the runtime benchmarks' sizes (stencil iterated longer),
# one worker on CPU 1.
KERNELS = {'mandel': ['1200', '1200', '300'], 'stencil': ['1000000', '200'], 'nbody': ['4096', '10'], 'sieve': ['100000000']}
ONE = dict(os.environ, NEO_THREADS='1')


def build():
    if os.environ.get('REUSE_BUILDS') == '1' and (OUT / 'server').exists(): return
    for label, tree in TREES:
        for path, name in (('bench/core/orders_stages.neo', 'orders'), ('examples/json-cli/main.neo', 'json-cli'),
                           ('bench/fetch/fetch.neo', 'fetch'), ('tests/fixtures/language_p384.neo', 'p384'),
                           *((f'examples/{k}.neo', k) for k in KERNELS), ('bench/core/orders_json.neo', 'orders_json'),
                           ('examples/library_bench.neo', 'library_bench')):
            profile = ['--dev'] if label in os.environ.get('NEO_DEV', '').split(',') else []
            subprocess.run(['./neo', 'build', path, '-o', str(OUT / f'{label}-{name}'), *profile], cwd=tree, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['go', 'build', '-o', str(OUT / 'server'), './server'], cwd=FETCH / 'go', check=True,
                   env=dict(os.environ, GOWORK='off'))
    rng = random.Random(7)
    (OUT / 'records.json').write_text(json.dumps([{'id': i, 'name': f'user{i}', 'score': rng.randrange(1000)} for i in range(200000)]))
    def openssl(*argv, **kw): return subprocess.run(['openssl', *argv], cwd=OUT, check=True, capture_output=True, **kw).stdout
    openssl('ecparam', '-name', 'secp384r1', '-genkey', '-noout', '-out', 'p384.key')
    public = openssl('ec', '-in', 'p384.key', '-pubout', '-outform', 'DER')[-97:]  # uncompressed point
    message = rng.randbytes(256)
    signature = openssl('dgst', '-sha384', '-sign', 'p384.key', input=message)
    (OUT / 'p384.record').write_bytes(bytes([1, 2, len(public)]) + public + bytes([len(signature)]) + signature + len(message).to_bytes(2, 'big') + message)


def timed(argv, env=None):
    started = time.perf_counter()
    r = subprocess.run(argv, capture_output=True, check=True, env=env)
    return time.perf_counter() - started, r.stdout


def main():
    out_path, rounds = sys.argv[1], int(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    build(); fetch.certificates(OUT, 'ec')
    port, tls_port = fetch.free_port(), fetch.free_port()
    server = subprocess.Popen(['taskset', '-c', '0', str(OUT / 'server'), str(port), str(tls_port), str(OUT / 'leaf.pem'), str(OUT / 'leaf.key')])
    try:
        for _ in range(100):
            try: socket.create_connection(('127.0.0.1', tls_port), timeout=1).close(); break
            except OSError: time.sleep(0.05)
        def https(label, path, count, size, keep):
            argv = ['taskset', '-c', '0', str(OUT / f'{label}-fetch'), str(tls_port), path, str(count), str(size), keep, str(OUT / 'ca.der')]
            lines = subprocess.run(argv, capture_output=True, text=True, check=True).stdout.split()
            if int(lines[1]) != count: raise SystemExit(f'{label} {path}: {lines[1]} of {count} good responses')
            return int(lines[0]) / count / 1e3, b''  # microseconds per request
        def p384(label):
            started = time.perf_counter()
            r = subprocess.run([str(OUT / f'{label}-p384'), '2', '200'], input=(OUT / 'p384.record').read_bytes(), capture_output=True, check=True)
            if r.stdout != b'valid=100\n': raise SystemExit(f'{label} p384: {r.stdout!r}')
            return time.perf_counter() - started, r.stdout
        cases = {
            'orders_stages mode 2 (s)': lambda label: timed([str(OUT / f'{label}-orders'), '2', '1000']),
            'orders_stages mode 3 (s)': lambda label: timed([str(OUT / f'{label}-orders'), '3', '1000']),
            'json-cli 200k records (s)': lambda label: (lambda t: (t[0], (OUT / f'{label}.out.json').read_bytes()))(
                timed([str(OUT / f'{label}-json-cli'), str(OUT / 'records.json'), str(OUT / f'{label}.out.json'), '500'])),
            'https new connection (us/request)': lambda label: https(label, '/hello', 300, 13, '0'),
            'https keep-alive 1 MiB (us/request)': lambda label: https(label, '/1m', 50, 1 << 20, '1'),
            'p384 verify x200 (s)': lambda label: p384(label),
            'orders_json 1000 x1000 (s)': lambda label: timed([str(OUT / f'{label}-orders_json'), '1000', '1000']),
            'library_bench documents x1M (s)': lambda label: timed([str(OUT / f'{label}-library_bench'), '0', '1000000']),
            'library_bench collections x1M (s)': lambda label: timed([str(OUT / f'{label}-library_bench'), '1', '1000000']),
            **{f'{k} {" ".join(args)} (s)': (lambda k, args: lambda label: timed(['taskset', '-c', '1', str(OUT / f'{label}-{k}'), *args], ONE))(k, args)
               for k, args in KERNELS.items()},
        }
        result = {'rounds': rounds, 'cases': {}}
        for case in cases: cases[case](TREES[0][0])  # warm-up
        for case, measure in cases.items():
            samples = {label: [] for label, _ in TREES}; outputs = {}
            for r in range(rounds):
                for label, _ in (TREES if r % 2 == 0 else TREES[::-1]):
                    value, output = measure(label)
                    samples[label].append(value); outputs[label] = hashlib.sha256(output).hexdigest()
            if len(set(outputs.values())) != 1: raise SystemExit(f'{case}: outputs differ between trees')
            result['cases'][case] = {label: {'median': statistics.median(v), 'samples': v} for label, v in samples.items()}
            print(case, ' '.join(f'{label} {statistics.median(v):.4g}' for label, v in samples.items()), flush=True)
            Path(out_path).write_text(json.dumps(result, indent=1))
    finally:
        server.kill()
    print('RUNTIME-CHECK-DONE')


if __name__ == '__main__':
    main()
