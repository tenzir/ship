---
title: Correct output stream for status messages
type: bugfix
authors:
  - mavam
  - claude
components:
  - cli
created: 2025-12-21T09:32:24.548841Z
---

Status messages now emit to stderr, allowing scripts to capture machine output from stdout without ANSI-colored status lines interfering.

Previously, commands like `release create` wrote both status messages and the version string to stdout, breaking workflows that capture output via `VERSION=$(uvx tenzir-changelog release create ...)`.
