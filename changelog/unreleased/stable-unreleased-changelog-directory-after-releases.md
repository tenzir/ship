---
title: Stable unreleased changelog directory after releases
type: bugfix
authors:
  - codex
created: 2026-06-15T15:08:28.822042Z
---

`release create` now keeps `unreleased/` anchored after consuming entries so Git no longer moves changelog entries from long-lived branches into the just-created release during rebases or merges.

This prevents entries for unreleased work from accidentally appearing in release notes that were already cut.
