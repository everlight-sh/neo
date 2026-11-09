#!/bin/sh
# Install Neo:  curl -fsSL https://neolang.dev/install.sh | sh
#
#   sh install.sh [--version X.Y.Z] [--archive FILE]
#
# Downloads a release from GitHub, checks it against the release's SHA256SUMS,
# unpacks it to $NEO_HOME/versions/<version> (NEO_HOME defaults to ~/.neo) and
# links $NEO_HOME/bin/neo to it. --archive installs a local release archive
# instead. Neo builds need Clang and a linker. Uninstall: rm -rf ~/.neo
set -eu

REPO=${NEO_REPO:-everlight-sh/neo}
DOWNLOAD=${NEO_DOWNLOAD_URL:-https://github.com/$REPO/releases/download}
NEO_HOME=${NEO_HOME:-$HOME/.neo}
version=
archive=

say() { printf '%s\n' "$*"; }
fail() { printf 'neo install: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case $1 in
    --version) [ $# -ge 2 ] || fail '--version needs a value'; version=${2#v}; shift 2 ;;
    --archive) [ $# -ge 2 ] || fail '--archive needs a file'; archive=$2; shift 2 ;;
    -h | --help) say 'usage: install.sh [--version X.Y.Z] [--archive FILE]'; exit 0 ;;
    *) fail "unknown option: $1" ;;
  esac
done

case "$(uname -s) $(uname -m)" in
  'Linux x86_64') platform=linux-x86_64 ;;
  'Linux aarch64' | 'Linux arm64') platform=linux-arm64 ;;
  'Darwin arm64') platform=darwin-arm64 ;;
  *) fail "Neo supports x86-64 and ARM64 Linux and ARM64 macOS, not $(uname -s) $(uname -m)" ;;
esac

fetch() {
  if command -v curl >/dev/null 2>&1; then curl -fsSL --retry 2 -o "$2" "$1"
  elif command -v wget >/dev/null 2>&1; then wget -q -O "$2" "$1"
  else fail 'needs curl or wget'
  fi
}

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d ' ' -f 1
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d ' ' -f 1
  else fail 'needs sha256sum or shasum to verify the download'
  fi
}

tmp=$(mktemp -d "${TMPDIR:-/tmp}/neo-install.XXXXXX")
trap 'rm -rf "$tmp"' EXIT INT TERM

if [ -z "$archive" ]; then
  if [ -z "$version" ]; then
    fetch "https://api.github.com/repos/$REPO/releases/latest" "$tmp/latest.json" || fail "cannot find the latest release of $REPO"
    version=$(sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' "$tmp/latest.json" | head -n 1)
    [ -n "$version" ] || fail "cannot read the latest version of $REPO"
  fi
  name=neo-$version-$platform.tar.gz
  say "Downloading Neo $version"
  fetch "$DOWNLOAD/v$version/$name" "$tmp/$name" || fail "cannot download $DOWNLOAD/v$version/$name"
  fetch "$DOWNLOAD/v$version/SHA256SUMS" "$tmp/SHA256SUMS" || fail "cannot download the release's SHA256SUMS"
  expected=$(awk -v name="$name" '$2 == name || $2 == "*" name { print $1 }' "$tmp/SHA256SUMS")
  [ -n "$expected" ] || fail "SHA256SUMS has no entry for $name"
  [ "$(sha256 "$tmp/$name")" = "$expected" ] || fail "checksum mismatch for $name; nothing was installed"
  archive=$tmp/$name
else
  [ -f "$archive" ] || fail "no such archive: $archive"
  say "Installing $archive (a local archive is not checksum-verified)"
fi

mkdir "$tmp/unpack"
tar -xzf "$archive" -C "$tmp/unpack" || fail "cannot unpack $archive"
set -- "$tmp"/unpack/neo-*
[ $# -eq 1 ] && [ -x "$1/neo" ] && [ -x "$1/bin/neoc" ] && [ -f "$1/VERSION" ] && [ -f "$1/PLATFORM" ] ||
  fail "$archive is not a native Neo release"
bundle_platform=$(cat "$1/PLATFORM")
[ "$bundle_platform" = "$platform" ] || fail "the archive is for $bundle_platform, this machine needs $platform"
release=$(cat "$1/VERSION")
case $release in '' | .* | *[!A-Za-z0-9.-]*) fail 'invalid release version' ;; esac
[ -z "$version" ] || [ "$release" = "$version" ] || fail "the archive holds Neo $release, not $version"

target=$NEO_HOME/versions/$release
mkdir -p "$NEO_HOME/versions" "$NEO_HOME/bin"
rm -rf "$target.partial"
mv "$1" "$target.partial"
rm -rf "$target"
mv "$target.partial" "$target"
ln -sf "../versions/$release/neo" "$NEO_HOME/bin/neo"
say "Installed Neo $release in $target"
say ''

if NEOC= NEO_ROOT= "$NEO_HOME/bin/neo" doctor; then ready=yes; else ready=; fi

case ":$PATH:" in
  *":$NEO_HOME/bin:"*) on_path=yes ;;
  *) on_path= ;;
esac
if [ -z "$on_path" ]; then
  say ''
  say 'Add neo to your PATH:'
  case ${SHELL:-} in
    */zsh) say "  echo 'export PATH=\"$NEO_HOME/bin:\$PATH\"' >> ~/.zshrc && exec zsh" ;;
    */bash) say "  echo 'export PATH=\"$NEO_HOME/bin:\$PATH\"' >> ~/.bashrc && exec bash" ;;
    */fish) say "  fish_add_path $NEO_HOME/bin" ;;
    *) say "  export PATH=\"$NEO_HOME/bin:\$PATH\"" ;;
  esac
fi
if [ -z "$ready" ]; then
  say ''
  say 'Neo is installed; install what neo doctor reports missing above, then run neo doctor again.'
fi
