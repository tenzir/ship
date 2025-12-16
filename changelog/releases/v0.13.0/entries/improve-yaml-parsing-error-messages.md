---
title: Improve YAML parsing error messages
type: change
authors:
  - mavam
  - claude
components:
  - cli
created: 2025-12-15T11:19:59.870643Z
---

Improve error messages when YAML frontmatter parsing fails in changelog entries. The error message now indicates which file has the problem and suggests to quote strings containing colons.
