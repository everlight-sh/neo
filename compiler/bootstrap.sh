#!/bin/sh
# Build the compiler with an existing native Neo release.
set -eu
root=$(CDPATH= cd -- "${0%/*}/.." && pwd -P)
output=$root/.neo-build/bin
seed=${NEOC:-}

while [ "$#" -gt 0 ]; do
    case $1 in
        --seed|-o|--output)
            [ "$#" -ge 2 ] || { printf '%s needs a value\n' "$1" >&2; exit 2; }
            if [ "$1" = --seed ]; then seed=$2; else output=$2; fi
            shift 2 ;;
        -h|--help) printf '%s\n' 'usage: compiler/bootstrap.sh [--seed NATIVE_NEOC] [-o DIRECTORY]'; exit 0 ;;
        *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
done

if [ -z "$seed" ]; then
    if [ -x "$root/.neo-build/bin/neoc" ]; then
        seed=$root/.neo-build/bin/neoc
    else
        seed=${NEO_HOME:-$HOME/.neo}/bin/neo
    fi
fi
[ -x "$seed" ] || { printf 'native Neo seed missing at %s\n' "$seed" >&2; exit 1; }
case $seed in /*) ;; *) seed=./$seed ;; esac
mkdir -p -- "$output"
# The compiler's recursive passes can need a larger stack on its own sources.
stack=$(ulimit -s)
hard_stack=$(ulimit -H -s)
wanted_stack=65536
case $hard_stack in
    ''|unlimited) ;;
    *) [ "$hard_stack" -ge "$wanted_stack" ] || wanted_stack=$hard_stack ;;
esac
case $stack in
    ''|unlimited) ;;
    *) [ "$stack" -ge "$wanted_stack" ] || ulimit -S -s "$wanted_stack" 2>/dev/null || : ;;
esac
export NEO_ROOT=$root
exec "$seed" build "$root/compiler/src/main.neo" --dev -o "$output/neoc"
