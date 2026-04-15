---
title: Release commit messages matching v tags
type: bugfix
authors:
  - mavam
  - codex
created: 2026-04-15T08:58:34.92952Z
---

The `release publish --commit` workflow now uses the tag-form version in generated release commits and annotated tag messages.

For example, publishing `v1.1.0` now creates `Release v1.1.0` instead of `Release 1.1.0`:

```sh
tenzir-ship release publish v1.1.0 --commit --tag --yes
```

This keeps generated release commits aligned with the corresponding Git tag and avoids mismatches in automation that expects the `v`-prefixed release identifier.
