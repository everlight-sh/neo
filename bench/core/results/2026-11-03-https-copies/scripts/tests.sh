#!/bin/bash
# The tests this change touches, in /root/new: unit tests, then the language
# suites for HTTP bodies, AES-GCM and TLS. Each suite's exit code follows it.
export PATH=/root/.cargo/bin:/usr/local/go/bin:/root/.bun/bin:$PATH
cd /root/new
echo "== unit"; python3 -m unittest tests.test_systems tests.test_proved_checks 2>&1 | tail -3
for t in http_large_body http_keepalive aes_language tls_language tls12_language tls_web_language http2_language; do
  echo "== $t"; python3 tests/$t.py 2>&1 | tail -8; echo "$t exit=${PIPESTATUS[0]}"
done
echo TESTS-DONE
