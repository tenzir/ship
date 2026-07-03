---
title: Required PR metadata validation
type: feature
authors:
  - codex
prs:
  - 34
created: 2026-07-03T10:07:28.575613Z
---

Projects can now set `require_pr: true` in their changelog configuration to make plain validation fail when an unreleased entry is missing `prs` metadata:

```sh
tenzir-ship validate
```

Use `tenzir-ship validate --lenient` in pre-push hooks to keep missing PR numbers as warnings until the pull request exists. Other validation errors still fail in lenient mode.
