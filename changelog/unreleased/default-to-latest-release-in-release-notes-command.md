---
title: Default to latest release in release notes command
type: feature
authors:
- mavam
- claude
components:
- cli
created: 2025-12-15T12:41:55.56468Z
---

Make the `release notes` command show the latest release by default when no identifier is provided. Previously, an explicit version identifier was required. Now omitting the identifier automatically resolves to the latest available release, streamlining the common case of viewing current release notes.
