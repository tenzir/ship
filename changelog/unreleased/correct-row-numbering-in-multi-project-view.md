---
title: Correct row numbering in multi-project view
type: bugfix
authors:
  - mavam
  - claude
created: 2025-12-22T12:06:03.645753Z
---

Row numbers in multi-project table view now count down from the newest entry, matching single-project behavior. The `show -c <row>` command also resolves row numbers correctly against the displayed table.
