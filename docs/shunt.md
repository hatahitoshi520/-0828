# shunt: cutting Claude Code's token usage

This project ships a small Claude Code plugin, `shunt`, that offloads pure
input/output work — reading large files, writing pattern-following
boilerplate — to a lightweight worker model instead of spending the main
session's tokens on it. It's a local implementation of the approach
Spotify described in ["Portal by Spotify cut my Claude Code token usage by
90%"](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90):
their engineer built "AiKA Modes" (`bulk-reader` and `code-writer`, backed
by Gemini 2.5 Flash) plus a `shunt` plugin that uses a `PreToolUse` hook to
force delegation, rather than relying on a CLAUDE.md instruction the model
might ignore.

## Why a hook instead of just an instruction

An instruction like "delegate large reads to another model" in CLAUDE.md is
optional context — Claude can still choose to `Read` a 2,000-line file
directly. A `PreToolUse` hook runs before the tool executes and can outright
block it, so the boundary holds mechanically even if the model never
consults the instructions. That's the core trick this repo copies.

## Pieces

- **`.claude/hooks/shunt_guard.py`** — the enforcement point. Registered in
  `.claude/settings.json` as a `PreToolUse` hook on `Read` and `Bash`. It
  blocks:
  - `Read` calls on files over `SHUNT_LINE_THRESHOLD` lines (default 350)
    when no `offset`/`limit` was given.
  - `cat`/`head`/`tail`/`less`/`more` in `Bash` on files over the threshold,
    unless the command already narrows the output (`head -n 50`, or a pipe
    through `grep`/`awk`/`sed`/etc.).

  Blocked calls exit with a message pointing at the `bulk-reader` skill;
  Claude sees this and can retry the right way.

- **`.claude/skills/bulk-reader/`** — a skill (`SKILL.md` + `bulk_read.sh`)
  that reads one or more files with a lightweight worker model and returns
  only a short answer to a specific question. The raw file contents never
  enter the main session's context.

- **`.claude/skills/code-writer/`** — a skill (`SKILL.md` + `code_write.sh`)
  that generates pattern-following boilerplate (tests, config blocks,
  repetitive sections) using a lightweight worker model, given one or more
  reference files whose conventions to imitate. With `--out`, the generated
  code is written straight to disk and never has to round-trip through the
  main session either.

- **`.claude/shunt/call_worker.sh`** — the shared "call the lightweight
  model" primitive both skills use. Spotify's version calls out to their
  internal Portal CLI; this version defaults to Claude Haiku via
  `claude -p --model haiku` (already authenticated in any environment
  running Claude Code), and can be redirected to any other CLI via the
  `SHUNT_WORKER_CMD` environment variable.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `SHUNT_LINE_THRESHOLD` | `350` | Line count above which `Read`/`cat`/`head`/`tail`/`less`/`more` get blocked. |
| `SHUNT_WORKER_MODEL` | `haiku` | Model alias passed to `claude -p --model` for the default worker backend. |
| `SHUNT_WORKER_CMD` | unset | If set, this command is used instead of the `claude` CLI; it receives the prompt on stdin and must print a plain-text answer to stdout. |

## What stays with the main session

Per Spotify's findings, this only makes sense for mechanical I/O — pulling
information out of a file, or emitting code that mirrors an existing
pattern. Debugging, architectural decisions, and safety-critical or
concurrency-sensitive code stay with the main session, since a lightweight
worker model can miss subtler issues (Spotify specifically called out
missed thread-safety bugs). The `code-writer` skill's `SKILL.md` says this
explicitly so Claude doesn't delegate work it shouldn't.
