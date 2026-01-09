---
title: Statistics command with adaptive view modes
type: feature
authors:
  - mavam
  - claude
created: 2026-01-09T10:49:45.103822Z
---

The `stats` command replaces the `--stats` flag and automatically adapts its display based on project structure. For single projects, it shows a vertical card view with detailed statistics organized into sections (Project, Releases, Entry Types, Entry Status). For multi-module projects, it displays a compact table comparing all modules side-by-side.

The vertical view presents project metadata, release history with exponentially weighted cadence calculations, entry type distribution with percentages, and shipped vs unreleased counts. The table view uses emoji headers for consistent visual scanning across both formats.

Additional options include `--table` to force table view regardless of project structure, and `--json` to export structured data for programmatic consumption.
