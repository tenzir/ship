---
title: Machine-readable version output from release create
type: feature
authors:
  - mavam
  - claude
created: 2025-12-19T09:55:58.380414Z
---

The `release create` command now outputs the created version to stdout, enabling shell scripting patterns like `VERSION=$(tenzir-changelog release create --minor --yes)`. All Rich output (tables, panels) now goes to stderr, keeping stdout clean for machine-readable results.
