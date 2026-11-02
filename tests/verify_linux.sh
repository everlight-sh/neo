#!/bin/sh
set -eu
./neo test
./neo build examples/http.neo -o .kernel-build/empty-http
python3 tests/freestanding_linux_smoke.py --binary .kernel-build/empty-http
