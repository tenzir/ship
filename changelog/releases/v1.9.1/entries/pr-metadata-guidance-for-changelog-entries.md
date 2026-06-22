---
title: PR metadata guidance for changelog entries
type: bugfix
authors:
  - mavam
  - codex
prs:
  - 31
created: 2026-06-22T06:27:16.220736Z
---

The changelog-entry skill no longer suggests passing `--pr` in the default `tenzir-ship add` command before a pull request number exists. Agents can rely on PR auto-inference once a pull request is open, or backfill `prs` after filing the PR.
