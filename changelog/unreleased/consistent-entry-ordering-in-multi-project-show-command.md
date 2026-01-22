---
title: Consistent entry ordering in multi-project show command
type: bugfix
authors:
  - mavam
  - claude
pr: 6
created: 2026-01-22T19:32:16.587667Z
---

The multi-project `show` command now displays changelog entries in chronological order, with the newest entry at the bottom of the table where users expect it. Previously, entries were sorted newest-first, which was inconsistent with single-project behavior and user expectations. This brings the multi-project display in line with the rest of the application's sorting behavior.
