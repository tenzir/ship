---
title: Release recovery instructions show actual branch name
type: bugfix
authors:
  - mavam
  - claude
pr: 5
created: 2026-01-22T19:01:49.721973Z
---

When a release fails during the branch push step, the recovery instructions now
display the actual branch name instead of a placeholder:

```
╭──────────────────── Release Progress (2/5) ────────────────────╮
│ ✔ git commit -m "Release v1.2.0"                               │
│ ✔ git tag -a v1.2.0 -m "Release v1.2.0"                        │
│ ✘ git push origin main:main                                    │
│ ○ git push origin v1.2.0                                       │
│ ○ gh release create v1.2.0 --repo tenzir/ship ...              │
╰────────────────────────────────────────────────────────────────╯
```

Previously, the failed step showed `git push origin <branch>:<branch>` instead
of the actual branch name.
