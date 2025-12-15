---
title: Add modules for nested changelog projects
type: feature
authors:
- mavam
- claude
created: 2025-12-13T14:02:41.007085Z
---

Modules are nested changelog projects discovered via a configurable glob pattern. Configure `modules` in `config.yaml` with a glob pattern like `../packages/*/changelog` to enable automatic discovery. The `show` command aggregates entries from all modules by default (use `--no-modules` to exclude), and `validate` checks all modules. Use the new `modules` command to list discovered modules with their paths.
