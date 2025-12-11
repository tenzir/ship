---
title: Format non-GitHub authors without @ prefix
type: change
components:
  - cli
authors:
  - mavam
  - claude
created: 2025-12-11T09:59:54.648556Z
---

Authors that contain spaces are now displayed without the `@` prefix.
Previously, all authors were rendered with `@` regardless of format, which
produced awkward output like `@Jane Smith` for non-GitHub users. Now only
GitHub-style handles (single words without spaces) receive the `@` prefix.
