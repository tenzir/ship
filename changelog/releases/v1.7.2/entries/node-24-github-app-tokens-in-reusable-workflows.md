---
title: Node 24 GitHub App tokens in reusable workflows
type: bugfix
authors:
  - mavam
  - codex
created: 2026-04-15T12:44:28.526615Z
---

The reusable release workflow no longer emits the Node 20 deprecation warning when it generates GitHub App tokens on GitHub-hosted runners.

Repositories that call `tenzir/ship/.github/workflows/release.yaml` now get clean release logs without extra configuration.
