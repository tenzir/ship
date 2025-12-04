---
title: Bootstrap changelog projects in changelog/ subdirectory
type: bugfix
author: claude
component: cli
created: 2025-12-04T04:55:13.813782Z
---

When running `tenzir-changelog add` in a fresh directory without an explicit `--root` flag, the CLI now creates the project structure in a `changelog/` subdirectory. This aligns bootstrap behavior with the documented project layout and the auto-detection of existing `changelog/` subdirectories introduced in v0.9.0.
