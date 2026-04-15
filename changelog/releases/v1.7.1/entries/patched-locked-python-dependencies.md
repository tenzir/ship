---
title: Patched locked Python dependencies
type: bugfix
authors:
  - mavam
  - codex
created: 2026-04-15T09:07:57.65802Z
---

The repository's locked Python dependencies now use patched upstream releases, including fixes for the open security advisories reported by Dependabot.

This refresh keeps local development and CI installs on maintained versions without changing normal `tenzir-ship` usage.
