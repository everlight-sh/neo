#!/bin/sh
# Install and exercise a release with only the compiler and system tools on PATH.
set -eu
root=$(CDPATH= cd -- "${0%/*}/.." && pwd -P)
archive=$1
version=$2
installer=${3:-$root/install.sh}
scratch=$(mktemp -d "${TMPDIR:-/tmp}/neo-release-check.XXXXXX")
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
mkdir "$scratch/tools" "$scratch/home"
for tool in clang ld ld.lld gzip curl tar uname readlink mktemp rm mv mkdir ln cat cut cmp grep awk sed head sha256sum shasum; do
    if path=$(command -v "$tool"); then
        case $path in /*) ln -s "$path" "$scratch/tools/$tool" ;; esac
    fi
done
native() {
    env -i PATH="$scratch/tools" HOME="$scratch/home" NEO_HOME="$scratch/home/.neo" \
        TMPDIR="$scratch" SDKROOT="${SDKROOT:-}" "$@"
}
neo="$scratch/home/.neo/bin/neo"
native /bin/sh "$installer" --archive "$archive"
[ "$(native "$neo" version)" = "Neo $version" ]
native "$neo" doctor
native "$neo" init "$scratch/project"
(
    cd "$scratch/project"
    [ "$(native "$neo" run)" = 'Hello, Neo!' ]
    mkdir -p tests
    printf '%s\n' 'fn test_release() -> bool = 2 * 3 == 6' > tests/release_test.neo
    results=$(native "$neo" test)
    printf '%s\n' "$results"
    printf '%s\n' "$results" | grep -Fxq 'neo test: 1 native cases, 0 failed'
)
