---
title: GitHub release title formatting
type: feature
authors:
  - codex
components:
  - cli
  - python
prs:
  - 38
created: 2026-07-06T17:30:00Z
---

The `release publish` command now formats GitHub release titles as
`PROJECT VERSION: TITLE` by default:

```sh
tenzir-ship release create v1.2.3 --title "Faster ingest"
tenzir-ship release publish v1.2.3
# GitHub release title: "Tenzir Ship v1.2.3: Faster ingest"
```

This keeps the release manifest title focused on the release itself while
making GitHub release pages show the project and version more clearly. To
customize the GitHub title, pass a format string with `$PROJECT`, `$VERSION`,
and `$TITLE` to `release publish --title` or
`Changelog.release_publish(title=...)`.
