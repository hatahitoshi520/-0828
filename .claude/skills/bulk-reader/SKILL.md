---
name: bulk-reader
description: Delegate reading of large files (or many files) to a lightweight worker model instead of loading their full contents into this session's context. Use whenever you need to answer a question about, or extract information from, one or more files that are large (long source files, generated files, logs, big config/data files) and you do not already know the exact line range you need. The PreToolUse hook in .claude/hooks/shunt_guard.py blocks direct Read/cat/head/tail/less/more calls on files over the size threshold and points here instead.
---

# bulk-reader

Purpose: answer questions about large files without spending this session's
tokens on their raw contents. A small worker model (Haiku by default) reads
the file(s) and returns only the short answer you need.

## When to use this instead of Read/Bash

- A file exceeds the line threshold enforced by the `shunt_guard` hook
  (350 lines by default, configurable via `SHUNT_LINE_THRESHOLD`).
- You need an answer synthesized from several files at once (e.g. "how do
  these 5 files implement X") rather than the raw text of any one of them.
- You do NOT already know the exact line range containing what you need —
  if you do, just call `Read` with `offset`/`limit` for that range, or pipe
  through `grep`/`sed`/`awk` in Bash; those stay fast paths and are not
  blocked.

## How to use it

Run the helper script with a precise question and the file path(s):

```bash
bash .claude/skills/bulk-reader/bulk_read.sh "Where is the retry logic for HTTP calls, and what backoff does it use?" src/net/HttpClient.java
```

Multiple files can be passed to get one synthesized answer:

```bash
bash .claude/skills/bulk-reader/bulk_read.sh "Which of these classes implement Comparable and how?" src/model/*.java
```

Only the script's stdout (the worker model's answer) enters your context —
never read the target file(s) directly first "just to check."

## Writing a good question

- Be specific about what you need (a method's behavior, a config value, a
  list of call sites) so the worker returns a short, targeted answer.
- Ask for exact quotes/line numbers when you'll need to reference or edit
  that spot afterward.
- If the first answer is insufficient, ask a sharper follow-up question
  rather than falling back to reading the raw file — that defeats the
  point.

## When NOT to use this

- Small files under the threshold: just `Read` them normally.
- Anything requiring judgment calls this session should own directly:
  debugging root-causing, architectural decisions, security-sensitive
  review. Use the worker only for mechanical extraction/summarization, per
  the project's shunt guidance (see `docs/shunt.md`).
