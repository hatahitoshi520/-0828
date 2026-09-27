#!/usr/bin/env bash
# bulk-reader worker: reads one or more (possibly large) files with a
# lightweight model and returns only a short answer to the caller's
# question, instead of loading the raw files into the main Claude session.
#
# Usage: bulk_read.sh "<question>" <file1> [file2 ...]
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: bulk_read.sh \"<question>\" <file1> [file2 ...]" >&2
  exit 1
fi

QUESTION="$1"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$(mktemp)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  echo "You are a fast bulk-reading assistant. Read the file(s) below and"
  echo "answer the question with the shortest accurate response possible:"
  echo "cite exact file/line references, quote only the lines needed, and"
  echo "omit any commentary the question did not ask for."
  echo
  echo "Question: $QUESTION"
  echo

  for f in "$@"; do
    if [[ ! -f "$f" ]]; then
      echo "=== $f ==="
      echo "(file not found)"
      continue
    fi
    echo "=== $f ==="
    cat "$f"
    echo
  done
} > "$PROMPT_FILE"

"$SCRIPT_DIR/../../shunt/call_worker.sh" "$PROMPT_FILE"
