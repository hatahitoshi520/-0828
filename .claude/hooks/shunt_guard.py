#!/usr/bin/env python3
"""PreToolUse hook: enforce delegation of bulk file reads to bulk-reader.

Blocks Read tool calls (and Bash cat/head/tail/less/more invocations) that
would pull a whole large file into this session's context, and points the
caller at the `bulk-reader` skill instead. Explicit, already-narrowed reads
(an offset/limit on Read, a small head/tail -n, or a cat piped through a
filter like grep/awk/sed) are left alone, since those don't blow up context.

Mirrors Spotify's "shunt" Claude Code plugin (see docs/shunt.md): a hook
enforces the boundary mechanically so it holds even when the model doesn't
think to consult CLAUDE.md instructions on its own.
"""
import json
import os
import re
import sys

LINE_THRESHOLD = int(os.environ.get("SHUNT_LINE_THRESHOLD", "350"))

# Images/binaries/PDFs: Read renders these directly (not as text tokens the
# same way), and bulk-reader can't usefully "read" them as text either, so
# the line-count guard doesn't apply.
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".pdf", ".mp4", ".mov", ".webm", ".mp3", ".wav", ".zip", ".gz",
    ".woff", ".woff2", ".ttf", ".eot",
}

READ_CMDS = ("cat", "head", "tail", "less", "more")
FILTER_CMD_RE = re.compile(r"\b(grep|awk|sed|cut|jq|wc|sort|uniq|comm|diff|column)\b")
SMALL_N_RE = re.compile(r"-n\s*(\d+)")


def count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def block(reason):
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def allow():
    sys.exit(0)


def check_read(tool_input):
    file_path = tool_input.get("file_path")
    if not file_path:
        allow()

    if os.path.splitext(file_path)[1].lower() in BINARY_EXTS:
        allow()

    # Explicit range: the caller already knows where to look.
    if tool_input.get("offset") or tool_input.get("limit"):
        allow()

    lines = count_lines(file_path)
    if lines is None or lines <= LINE_THRESHOLD:
        allow()

    block(
        f"shunt: {file_path} has {lines} lines (> {LINE_THRESHOLD}). "
        "Reading it whole would spend a lot of this session's context on "
        "input tokens. Use the bulk-reader skill instead, e.g.:\n"
        f'  bash .claude/skills/bulk-reader/bulk_read.sh "<your question>" {file_path}\n'
        "If you only need a specific part, retry Read with an explicit "
        "offset/limit instead."
    )


def find_command_targets(command, cmd_name):
    """Best-effort extraction of file path arguments after `cmd_name`."""
    pattern = re.compile(rf"(?:^|[;&|]\s*)\s*{cmd_name}\b([^|;&]*)")
    targets = []
    for m in pattern.finditer(command):
        args_str = m.group(1)
        for tok in args_str.split():
            if tok.startswith("-"):
                continue
            targets.append(tok)
    return targets


def check_bash(tool_input):
    command = tool_input.get("command", "")
    if not command:
        allow()

    segments = [s.strip() for s in command.split("|")]
    first = segments[0]
    rest = segments[1:]

    used_cmd = None
    for c in READ_CMDS:
        if re.search(rf"(?:^|[;&|]\s*)\s*{c}\b", first):
            used_cmd = c
            break
    if used_cmd is None:
        allow()

    # head -n N / tail -n N with a small N is an explicit narrow read.
    n_match = SMALL_N_RE.search(first)
    if used_cmd in ("head", "tail") and n_match and int(n_match.group(1)) <= LINE_THRESHOLD:
        allow()

    # Piped through a filter (grep/awk/sed/...) narrows the output.
    if any(FILTER_CMD_RE.search(seg) for seg in rest):
        allow()

    targets = find_command_targets(command, used_cmd)
    large_targets = []
    for t in targets:
        if os.path.splitext(t)[1].lower() in BINARY_EXTS:
            continue
        lines = count_lines(t)
        if lines is not None and lines > LINE_THRESHOLD:
            large_targets.append((t, lines))

    if not large_targets:
        allow()

    details = ", ".join(f"{t} ({n} lines)" for t, n in large_targets)
    block(
        f"shunt: `{used_cmd}` on {details} exceeds the {LINE_THRESHOLD}-line "
        "threshold for direct reads in Bash. Use the bulk-reader skill "
        "instead, e.g.:\n"
        f'  bash .claude/skills/bulk-reader/bulk_read.sh "<your question>" {targets[0]}\n'
        "Or narrow the read yourself first, e.g. `head -n 100 "
        f"{targets[0]}` or pipe through grep/awk/sed."
    )


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        allow()
        return

    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input", {}) or {}

    if tool_name == "Read":
        check_read(tool_input)
    elif tool_name == "Bash":
        check_bash(tool_input)
    else:
        allow()


if __name__ == "__main__":
    main()
