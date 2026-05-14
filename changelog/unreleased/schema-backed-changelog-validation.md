---
title: Schema-backed changelog validation
type: bugfix
created: 2026-05-13T00:00:00Z
---

Validate changelog entry metadata and release manifests with JSON Schema so malformed
fields such as non-numeric pull request references are reported instead of silently
passing validation.
