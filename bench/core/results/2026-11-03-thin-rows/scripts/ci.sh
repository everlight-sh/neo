#!/bin/bash
# The verify.yml steps, as root, in /root/new.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
cd /root/new
(cd examples/jsx-ssr && bun install --frozen-lockfile >/dev/null 2>&1) || echo "bun install failed"
echo "== neo test"; ./neo test 2>&1 | tail -25; echo "neo test exit=${PIPESTATUS[0]}"
echo "== freestanding smoke"; ./neo build examples/http.neo -o .kernel-build/ci-http && python3 tests/freestanding_linux_smoke.py --binary .kernel-build/ci-http 2>&1 | tail -3; echo "exit=${PIPESTATUS[0]}"
echo "== reproducible release"; ./neo release -o .kernel-build/release-a.tar.gz >/dev/null 2>&1 && ./neo release -o .kernel-build/release-b.tar.gz >/dev/null 2>&1 && cmp .kernel-build/release-a.tar.gz .kernel-build/release-b.tar.gz && echo "release reproducible"
echo "== language/crypto/TLS"
./neo build tests/fixtures/language_kernel.neo -o .kernel-build/ci-kernel && ./neo build tests/fixtures/language_crypto.neo -o .kernel-build/ci-crypto && ./neo build tests/fixtures/language_tls.neo -o .kernel-build/ci-tls && \
  python3 tests/language_freestanding.py --kernel .kernel-build/ci-kernel --crypto .kernel-build/ci-crypto --tls .kernel-build/ci-tls 2>&1 | tail -5; echo "exit=${PIPESTATUS[0]}"
echo CI-DONE
