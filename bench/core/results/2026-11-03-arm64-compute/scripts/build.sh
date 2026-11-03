# build.sh SRC OUT : build neo-<program> executables from tree SRC into OUT
set -e
SRC=$1; OUT=$2; mkdir -p $OUT
cd $SRC
for p in mandel stencil nbody sieve; do ./neo build examples/$p.neo -o $OUT/neo-$p --no-cache >/dev/null; done
ls -la $OUT
