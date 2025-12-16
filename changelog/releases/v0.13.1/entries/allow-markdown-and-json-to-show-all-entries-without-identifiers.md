---
title: Allow --markdown and --json to show all entries without identifiers
type: change
authors:
  - mavam
  - claude
created: 2025-12-16T15:24:31.205878Z
---

The `show` command's `--markdown` and `--json` export formats previously
required at least one identifier argument. Now they work like the default
table view and display all entries when no identifiers are specified.
