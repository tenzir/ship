---
title: Confirm release publishing before mutating anything
type: bugfix
authors:
  - claude
prs:
  - 41
created: 2026-08-04T08:47:24.381906Z
---

`release publish` asked for confirmation only after the commit, tag, and both pushes had already reached the remote, so declining could not undo them. The prompt now appears before the first mutation and lists every step it is about to run.
