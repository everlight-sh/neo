#!/bin/sh
# Run by Dockerfile.linux-test: build the compiler from the native seed, check
# that it rebuilds itself byte for byte, then run every native test case. As
# root, the runtime cases also rerun their static binaries in an empty chroot.
set -eu
seed=${NEO_SEED:-/opt/neo-seed/bin/neo}
./compiler/bootstrap.sh --seed "$seed"
./compiler/bootstrap.sh
cp .neo-build/bin/neoc .neo-build/neoc-self
./compiler/bootstrap.sh
cmp .neo-build/bin/neoc .neo-build/neoc-self
if [ "$(id -u)" = 0 ]; then
  NEO_TEST_ROOT_CHECKS=1 ./neo test
else
  ./neo test
fi
