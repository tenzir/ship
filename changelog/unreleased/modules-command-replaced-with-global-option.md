---
title: Modules command replaced with global option
type: breaking
authors:
  - mavam
  - claude
created: 2026-01-09T06:23:52.726382Z
---

The `modules` command has been removed. Use the `--show-modules` global option instead to list discovered modules.

Migration:
```bash
# Before
tenzir-changelog modules

# After
tenzir-changelog --show-modules
```

The PATH column now displays clean relative paths (for example, `plugins/brand/changelog`) instead of paths with `../` prefixes (for example, `../plugins/brand/changelog`).
