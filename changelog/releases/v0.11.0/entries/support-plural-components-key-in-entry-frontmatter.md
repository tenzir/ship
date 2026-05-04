---
title: Support plural components key in entry frontmatter
type: feature
authors:
  - mavam
components:
  - cli
  - python
created: 2025-12-05T16:20:03.231548Z
---

Entries now support both `component` (singular) and `components` (plural) keys in YAML frontmatter, following the existing patterns for `author`/`authors` and `pr`/`prs`. This allows entries to have multiple components. The CLI `--component` option can be repeated for multiple values.
