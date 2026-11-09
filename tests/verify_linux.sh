#!/bin/sh
set -eu
./neoc.sh test
./neoc.sh build examples/http.neo -o .kernel-build/empty-http
python3 tests/freestanding_linux_smoke.py --binary .kernel-build/empty-http
