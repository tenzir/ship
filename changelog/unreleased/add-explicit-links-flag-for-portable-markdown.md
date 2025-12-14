---
title: Add `--explicit-links` flag for portable Markdown
type: feature
authors:
- mavam
- claude
components:
- cli
created: 2025-12-14T08:52:33.87606Z
---

The `show` and `release notes` commands now accept `--explicit-links` to render `@mentions` and `#PR` references as full Markdown links. Use this flag when exporting release notes to documentation sites or other renderers that lack GitHub's auto-linking.
