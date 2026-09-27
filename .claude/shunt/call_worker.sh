#!/usr/bin/env bash
# Shared worker-model caller for the shunt token-reduction system.
#
# Runs a prompt on a lightweight "worker" model instead of the main Claude
# session, so bulky input/output never enters the main session's context.
# Mirrors Spotify's Portal/AiKA Modes worker-model role (they use Gemini 2.5
# Flash); here the worker defaults to Claude Haiku via the `claude` CLI's
# headless print mode, which is already authenticated in this environment.
#
# Override the backend with SHUNT_WORKER_CMD to point at any other CLI
# (e.g. a `gemini` or `portal` command) that reads a prompt on argv/stdin
# and prints a plain-text answer to stdout.
#
# Usage: call_worker.sh <prompt-file>
set -euo pipefail

PROMPT_FILE="${1:?usage: call_worker.sh <prompt-file>}"
MODEL="${SHUNT_WORKER_MODEL:-haiku}"

if [[ -n "${SHUNT_WORKER_CMD:-}" ]]; then
  # Custom backend: receives the prompt on stdin.
  eval "$SHUNT_WORKER_CMD" < "$PROMPT_FILE"
else
  claude -p --model "$MODEL" --allowedTools "" < "$PROMPT_FILE"
fi
