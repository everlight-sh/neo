#!/bin/sh
# Explicit Python reference compiler and legacy project tooling.
set -eu
reference_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
export PYTHONPATH="$reference_root${PYTHONPATH:+:$PYTHONPATH}"
exec "${NEO_PYTHON:-python3}" -m neoc "$@"
