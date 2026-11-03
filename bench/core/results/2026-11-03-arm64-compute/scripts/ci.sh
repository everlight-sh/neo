# ci.sh SRC : every step of .github/workflows/verify.yml on a fresh copy of SRC (run as root, so no sudo)
set -e
export PATH=/root/.bun/bin:/usr/local/go/bin:/root/.cargo/bin:$PATH
rm -rf /root/ci && cp -r $1 /root/ci && cd /root/ci && rm -rf .kernel-build
(cd examples/jsx-ssr && bun install --frozen-lockfile)
echo "== ./neo test"; time ./neo test
echo "== Empty-root runtime audit"
./neo build examples/http.neo -o .kernel-build/ci-http && python3 tests/freestanding_linux_smoke.py --binary .kernel-build/ci-http
echo "== Reproducible compiler bundle"
./neo release -o .kernel-build/release-a.tar.gz && ./neo release -o .kernel-build/release-b.tar.gz && cmp .kernel-build/release-a.tar.gz .kernel-build/release-b.tar.gz && sha256sum .kernel-build/release-*.tar.gz
echo "== Empty-root language, crypto and TLS"
./neo build tests/fixtures/language_kernel.neo -o .kernel-build/ci-kernel
./neo build tests/fixtures/language_crypto.neo -o .kernel-build/ci-crypto
./neo build tests/fixtures/language_tls.neo -o .kernel-build/ci-tls
python3 tests/language_freestanding.py --kernel .kernel-build/ci-kernel --crypto .kernel-build/ci-crypto --tls .kernel-build/ci-tls
echo CI-ALL-STEPS-OK
