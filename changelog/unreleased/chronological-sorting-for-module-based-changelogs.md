---
title: Chronological sorting for module-based changelogs
type: change
authors:
  - mavam
  - claude
components:
  - cli
created: 2025-12-21T11:11:33.804025Z
---

The `show` command now sorts entries by date across all modules, placing the latest entries at the bottom of the table. Previously, entries were grouped by project first, which scattered recent changes throughout the output based on module name order.
