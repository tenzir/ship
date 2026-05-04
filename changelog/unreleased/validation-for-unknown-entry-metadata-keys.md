---
title: Validation for unknown entry metadata keys
type: bugfix
authors:
  - mavam
  - codex
prs:
  - 23
created: 2026-05-04T14:53:17.897994Z
---

The `validate` command now reports unknown changelog entry metadata keys instead of silently accepting them. This catches misspelled fields such as `co-authors` early, before they are ignored by release workflows.
