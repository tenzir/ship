---
title: Enforce changelog structure for releases and command warnings
type: bugfix
authors:
  - mavam
  - codex
created: 2026-02-28T00:00:00Z
---

Release commands now validate changelog directory structure before they run and fail fast when it is invalid.

`release create` and `release publish` now stop with explicit errors when stray files or directories are detected (for example, an unexpected `changelog/next/` directory). Other commands (`show`, `add`, `stats`, and `release version`) emit warnings so layout problems are visible earlier, while `validate` reports full structural issues as regular validation errors.
