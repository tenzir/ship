---
title: Pi package and skill for release engineering
type: feature
authors:
  - mavam
  - claude
  - codex
pr: 11
created: 2026-03-01T10:17:24.939854Z
---

The `pi-tenzir-ship` package provides a skill for AI coding agents to perform
release engineering tasks. Install it in Pi with:

```sh
pi install npm:pi-tenzir-ship
```

Then activate it with `/skill:tenzir-ship`.

The skill covers adding changelog entries, cutting standard and module releases,
triggering GitHub Actions release workflows, and publishing releases to GitHub.
