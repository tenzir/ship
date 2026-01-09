---
title: Markdown table formatting in release notes
type: bugfix
authors:
  - mavam
  - claude
components:
  - cli
created: 2026-01-09T11:31:01.00296Z
---

Markdown tables in release notes and entry descriptions now render correctly. Previously, tables were collapsed into a single line because the `normalize_markdown()` function lacked GFM (GitHub Flavored Markdown) support.

The fix adds the `mdformat-gfm` plugin to enable proper table formatting. This ensures migration guides, comparison tables, and other tabular content display as intended in both CLI output and exported markdown files.
