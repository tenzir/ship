This release fixes two bugs: the multi-project `show` command now displays entries in consistent chronological order, and release recovery instructions show the actual branch name instead of a placeholder.

## 🐞 Bug fixes

### Consistent entry ordering in multi-project show command

The multi-project `show` command now displays changelog entries in chronological order, with the newest entry at the bottom of the table where users expect it. Previously, entries were sorted newest-first, which was inconsistent with single-project behavior and user expectations. This brings the multi-project display in line with the rest of the application's sorting behavior.

*By @mavam and @claude in #6.*

### Release recovery instructions show actual branch name

When a release fails during the branch push step, the recovery instructions now display the actual branch name instead of a placeholder:

```
╭──────────────────── Release Progress (2/5) ────────────────────╮
│ ✔ git commit -m "Release v1.2.0"                               │
│ ✔ git tag -a v1.2.0 -m "Release v1.2.0"                        │
│ ✘ git push origin main:main                                    │
│ ○ git push origin v1.2.0                                       │
│ ○ gh release create v1.2.0 --repo tenzir/ship ...              │
╰────────────────────────────────────────────────────────────────╯
```

Previously, the failed step showed `git push origin <branch>:<branch>` instead of the actual branch name.

*By @mavam and @claude in #5.*
