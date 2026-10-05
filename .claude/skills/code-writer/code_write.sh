#!/usr/bin/env bash
# code-writer worker: generates boilerplate/pattern-following code with a
# lightweight model, using one or more reference files so the output
# matches this project's existing naming/style conventions. If a target
# path is given, the generated code is written straight to disk and never
# has to pass back through the main Claude session's context.
#
# Usage: code_write.sh "<spec>" --ref <reference-file> [--ref <reference-file> ...] [--out <target-file>]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: code_write.sh \"<spec>\" --ref <reference-file> [--ref <reference-file> ...] [--out <target-file>]" >&2
  exit 1
fi

SPEC="$1"
shift

REFS=()
OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)
      REFS+=("$2")
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ ${#REFS[@]} -eq 0 ]]; then
  echo "error: at least one --ref <reference-file> is required so the" >&2
  echo "generated code follows this project's existing patterns" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$(mktemp)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  echo "You are a fast pattern-matching code generator. Study the reference"
  echo "file(s) below for this project's naming conventions, style, and"
  echo "structure, then produce code that satisfies the spec by imitating"
  echo "those patterns. Output ONLY the final code, no explanations, no"
  echo "markdown code fences."
  echo
  echo "Spec: $SPEC"
  echo

  for f in "${REFS[@]}"; do
    if [[ ! -f "$f" ]]; then
      echo "=== reference: $f ==="
      echo "(file not found)"
      continue
    fi
    echo "=== reference: $f ==="
    cat "$f"
    echo
  done
} > "$PROMPT_FILE"

if [[ -n "$OUT" ]]; then
  "$SCRIPT_DIR/../../shunt/call_worker.sh" "$PROMPT_FILE" > "$OUT"
  echo "wrote generated code to $OUT (not loaded into the main session)"
else
  "$SCRIPT_DIR/../../shunt/call_worker.sh" "$PROMPT_FILE"
fi
