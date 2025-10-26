---
title: Add components to changelog entries
type: feature
authors:
- codex
created: 2025-10-26
---

Entries can now record an optional `component` tag (for example `cli`, `docs`, or `ci`). If you skip the field—as we do in this repository—the CLI behaves exactly as before. When a component is present, `tenzir-changelog show` adds a dedicated column, release notes surface the label, and Markdown/JSON exports include the value.

Projects that want per-component slices can pass `--component <name>` to `tenzir-changelog add` and reuse the same flag on `show` when filtering a backlog or exporting a release.

Finally, the table view only renders the Component column when at least one entry in the result set uses the feature, keeping homogeneous changelog streams clutter-free.
