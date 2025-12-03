---
title: Support singular pr and author keys
type: feature
authors:
- claude
- mavam
pr: 2
component: cli
created: 2025-12-03
---

Changelog entries can now use the singular `pr` and `author` keys in YAML frontmatter as shorthand for single values. For example, instead of writing:

```yaml
prs:
  - 42
authors:
  - codex
```

You can now write:

```yaml
pr: 42
author: codex
```

Both forms are supported, and the singular form is automatically normalized to the plural form when the entry is read. Using both forms in the same entry is an error.
