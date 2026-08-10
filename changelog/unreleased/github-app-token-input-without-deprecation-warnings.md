---
title: GitHub App token input without deprecation warnings
type: bugfix
authors:
  - mavam
  - codex
prs:
  - 43
created: 2026-08-10T07:58:01.413938Z
---

The reusable release workflow no longer emits a deprecation warning when
it generates a GitHub App token. Existing App IDs remain supported and require
no configuration changes.
