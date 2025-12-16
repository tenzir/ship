---
title: Remove multi-project mode
type: breaking
authors:
- mavam
- claude
components:
- cli
created: 2025-12-15T15:18:38.275137Z
---

Remove the multi-project mode feature that allowed specifying multiple `--root` flags to coordinate releases across projects.

Users who need monorepo support should use the `modules` feature instead, which was designed for this purpose and remains fully supported.

**Migration guide:**
- Replace `--root proj1 --root proj2 --root proj3` with `modules` configuration in `config.yaml`
- Single `--root` path continues to work as before
- The Python API now accepts a single `root` parameter instead of `roots` sequence
