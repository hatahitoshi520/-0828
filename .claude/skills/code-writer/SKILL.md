---
name: code-writer
description: Delegate generation of boilerplate or pattern-following code (tests that mirror existing tests, config/data file scaffolds, type definitions, repetitive CRUD-style code) to a lightweight worker model, using one or more existing project files as the style/pattern reference. Use this for mechanical "write more of the same shape" work, not for code requiring debugging, architectural judgment, or security-sensitive logic — that stays with this session.
---

# code-writer

Purpose: produce code that imitates existing project patterns (a new test in
the shape of existing tests, a new config entry matching existing ones, a
new type mirroring a sibling type) without spending this session's input
tokens reading the reference file in full or its output tokens writing the
result — a small worker model does both, and can write straight to disk.

## When to use this instead of writing the code yourself

- The task is "make N that looks like existing M": a new test alongside 20
  existing tests, a new landing-page section that follows the existing
  section markup, a new config block shaped like its neighbors, a
  boilerplate type/interface.
- You can point at a concrete reference file (or files) whose conventions
  the output should follow. A reference file is required — this is what
  keeps generated code consistent with the project instead of generic.

## When NOT to use this

- Anything needing real reasoning: debugging, concurrency/thread-safety,
  security-sensitive code, non-obvious architectural choices, or a change
  where getting the pattern subtly wrong would be costly. Do that yourself.
- One-off code with no existing pattern to imitate.

## How to use it

Always pass at least one `--ref` file. Add `--out` to write the result
directly to disk (recommended when the output would otherwise be large —
the generated code then never enters this session's context at all):

```bash
bash .claude/skills/code-writer/code_write.sh \
  "Add a new pricing card section for the 'Team' plan, same structure as the existing plan cards" \
  --ref index.html \
  --out /tmp/team-card-snippet.html
```

Then inspect the small diff/snippet yourself (e.g. with a targeted `Read`
or `grep`) before merging it in, rather than re-reading the whole reference
file again.

Without `--out`, the generated code is printed to stdout and does enter
your context — prefer `--out` whenever the snippet is more than a few
lines.

## Multiple references

Pass `--ref` more than once when the pattern spans files (e.g. a test file
plus the class under test):

```bash
bash .claude/skills/code-writer/code_write.sh \
  "Add a test for the new discount calculation, following the existing test style" \
  --ref tests/PricingTest.java \
  --ref src/Pricing.java \
  --out tests/DiscountTest.java
```
