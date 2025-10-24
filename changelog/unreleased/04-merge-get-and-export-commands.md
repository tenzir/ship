---
title: Merge get and export commands
type: breaking
authors:
- codex
created: 2025-10-22
---

Merged the get and export flows so `tenzir-changelog get` displays entries in the terminal or exports them as Markdown/JSON via `--format`. Added the `-c` short flag for compact exports, accepted identifiers `unreleased` and `-` across `list` and `get`, and simplified release creation to `tenzir-changelog release <version>`.
