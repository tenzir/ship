---
title: Release-scoped changelog entry IDs
type: bugfix
authors:
  - mavam
  - codex
prs:
  - 39
created: 2026-07-21T11:07:32.400232Z
---

Release creation now treats changelog entry IDs as unique within each release
instead of across the entire project history. Reusing a slug from an older
release remains eligible for automatic version bumps, validation checks
release-local references, and show output preserves every occurrence with its
release context.
