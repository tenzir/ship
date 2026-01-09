---
title: Scope filtering flags replaced with positional tokens
type: breaking
authors:
  - mavam
  - claude
created: 2026-01-09T15:01:12.703029Z
---

The show command now uses positional scope tokens instead of flags to filter entries. The `--all`, `--released`, `--unreleased`, and `--latest` flags have been removed in favor of cleaner positional identifiers.

Use `show unreleased`, `show released`, `show latest`, or `show all` to filter entries by scope. The `--release` flag now purely controls presentation (grouping and metadata display) rather than affecting which entries are shown.

This change provides clearer separation between **what to show** (scope) and **how to show it** (presentation), making the command interface more intuitive.

**Breaking change:** `show --release` without identifiers now shows **all** entries grouped by release, whereas previously it defaulted to showing only the latest release. Use `show latest --release` to restore the previous behavior.

**Migration examples:**

- `show --unreleased` → `show unreleased`
- `show --released` → `show released`
- `show --latest` → `show latest`
- `show --all` → `show all` or just `show`
- `show --release` → `show latest --release` (to get previous behavior)
- `show --release --latest` → `show latest --release`
