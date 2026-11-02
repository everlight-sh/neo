#!/bin/sh
# Logged compiler wrapper for the agent-in-the-loop experiment.
# Usage (from anywhere): experiments/agent-loop/neoc.sh <task-dir> build|check <file.neo> [args]
# Appends every invocation and its full output to <task-dir>/attempts.log.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK="$1"; shift
mkdir -p "$TASK"
{
  echo "=== $(date '+%H:%M:%S') neoc $*"
  (cd "$ROOT" && python3 -m neoc "$@") 2>&1
  echo "=== exit $?"
} | tee -a "$TASK/attempts.log"
