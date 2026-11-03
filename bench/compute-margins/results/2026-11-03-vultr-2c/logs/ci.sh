set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -q && apt-get install -y -q clang lld python3 binutils openssl golang-go git unzip
curl -fsSL https://bun.sh/install | bash -s bun-v1.3.13
export PATH=/root/.bun/bin:$PATH
mkdir -p /root/ci && tar xzf /root/commit.tgz -C /root/ci && cd /root/ci
(cd examples/jsx-ssr && bun install --frozen-lockfile)
set +e
clang --version | head -1; bun --version; go version; uname -r; lscpu | grep "Model name"
./neo test > /root/ci-test.log 2>&1; echo "STEP neo-test exit=$?"
tail -40 /root/ci-test.log
mkdir -p .kernel-build
./neo build examples/http.neo -o .kernel-build/ci-http && python3 tests/freestanding_linux_smoke.py --binary .kernel-build/ci-http; echo "STEP freestanding-http exit=$?"
./neo release -o .kernel-build/release-a.tar.gz && ./neo release -o .kernel-build/release-b.tar.gz && cmp .kernel-build/release-a.tar.gz .kernel-build/release-b.tar.gz; echo "STEP reproducible-release exit=$?"
./neo build tests/fixtures/language_kernel.neo -o .kernel-build/ci-kernel && ./neo build tests/fixtures/language_crypto.neo -o .kernel-build/ci-crypto && ./neo build tests/fixtures/language_tls.neo -o .kernel-build/ci-tls && python3 tests/language_freestanding.py --kernel .kernel-build/ci-kernel --crypto .kernel-build/ci-crypto --tls .kernel-build/ci-tls; echo "STEP language-freestanding exit=$?"
echo CI-DONE
