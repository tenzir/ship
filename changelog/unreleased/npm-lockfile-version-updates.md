---
title: npm lockfile version updates
type: feature
authors:
  - codex
prs:
  - 30
created: 2026-06-18T09:26:46.814972Z
---

The `release create` command now keeps npm lockfiles in sync when it updates `package.json` versions.

When a sibling `package-lock.json` exists, `tenzir-ship` updates the lockfile root package version metadata alongside `package.json`, including already-current manifests with stale lockfiles. This keeps generated release commits consistent without requiring every workflow caller to add an npm-specific post-create hook.
