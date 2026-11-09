#!/bin/sh
set -eu
[ "$#" -eq 3 ] || { printf '%s\n' 'usage: assemble-native-release.sh VERSION EPOCH DIST' >&2; exit 2; }
version=$1
epoch=$2
dist=$(CDPATH= cd -- "$3" && pwd -P)
stage=$(mktemp -d "$dist/universal.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM
umask 022
for platform in linux-x86_64 linux-arm64 darwin-arm64; do
    mkdir -p "$stage/$platform"
    tar -xzf "$dist/neo-$version-$platform.tar.gz" -C "$stage/$platform"
    test "$(cat "$stage/$platform/neo-$version/VERSION")" = "$version"
    test "$(cat "$stage/$platform/neo-$version/PLATFORM")" = "$platform"
done
base=$stage/linux-x86_64/neo-$version
for platform in linux-arm64 darwin-arm64; do
    diff -r -x bin -x PLATFORM -x README.md -x MANIFEST.json \
        "$base" "$stage/$platform/neo-$version"
done
mv "$base/bin/neoc" "$base/bin/neoc-linux-x86_64"
for platform in linux-arm64 darwin-arm64; do
    cp "$stage/$platform/neo-$version/bin/neoc" "$base/bin/neoc-$platform"
done
cat > "$base/bin/neoc" <<'LAUNCHER'
#!/bin/sh
set -eu
case "$(uname -s):$(uname -m)" in
    Linux:x86_64) platform=linux-x86_64 ;;
    Linux:aarch64|Linux:arm64) platform=linux-arm64 ;;
    Darwin:arm64) platform=darwin-arm64 ;;
    *) printf '%s\n' 'Neo has no native compiler for this platform.' >&2; exit 1 ;;
esac
exec "${0%/*}/neoc-$platform" "$@"
LAUNCHER
chmod 0755 "$base/bin/neoc"
printf 'multi-platform\n' > "$base/PLATFORM"
sed 's/Native compiler for linux-x86_64\./Native compilers for Linux x86-64, Linux ARM64, and macOS ARM64./' \
    "$base/README.md" > "$stage/README"
mv "$stage/README" "$base/README.md"
(
    cd "$base"
    find . -type f ! -name MANIFEST.json > "$stage/files"
    LC_ALL=C sort "$stage/files" > "$stage/sorted-files"
    printf '{\n  "files": {\n'
    separator=
    while IFS= read -r file; do
        name=${file#./}
        case $name in *[!A-Za-z0-9_./-]*) exit 1 ;; esac
        digest=$(sha256sum "$file")
        digest=${digest%% *}
        printf '%s    "%s": "%s"' "$separator" "$name" "$digest"
        separator=$(printf ',\n.')
        separator=${separator%.}
    done < "$stage/sorted-files"
    printf '\n  },\n  "platform": "multi-platform",\n  "version": "%s"\n}\n' "$version"
) > "$base/MANIFEST.json"
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime="@$epoch" --format=ustar \
    -C "$stage/linux-x86_64" -cf "$stage/bundle.tar" "neo-$version"
gzip -n -9 -c "$stage/bundle.tar" > "$stage/bundle.tar.gz"
mv "$stage/bundle.tar.gz" "$dist/neo-$version.tar.gz"
(
    cd "$dist"
    sha256sum "neo-$version.tar.gz" "neo-$version-linux-x86_64.tar.gz" \
        "neo-$version-linux-arm64.tar.gz" "neo-$version-darwin-arm64.tar.gz" > SHA256SUMS
    sha256sum -c SHA256SUMS
)
