---
title: Fix overly broad version string detection in show command
type: bugfix
authors:
  - mavam
  - claude
created: 2026-01-26T19:19:09.28115Z
---

The `show` command no longer misidentifies changelog entry IDs as release versions. Previously, entries with IDs containing version-like patterns (e.g., `v1...`) were incorrectly treated as releases.
