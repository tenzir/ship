---
title: Fix YAML list indentation in entry frontmatter
type: change
authors:
- mavam
- claude
components:
- python
created: 2025-12-15T11:25:58.1922Z
---

Ensure list items under keys like `authors:` and `components:` are indented with 2 spaces in YAML frontmatter. Added a custom `_IndentedDumper` class that overrides `increase_indent` to enforce consistent YAML formatting conventions when writing changelog entry files.
