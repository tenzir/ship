---
title: GitHub release title formatting
type: feature
authors:
  - IyeOnline
  - mavam
  - codex
components:
  - cli
  - python
prs:
  - 38
created: 2026-07-06T17:30:00Z
---

The `release publish` command now formats GitHub release titles as
`PROJECT VERSION: TITLE` by default when the release has a title:

```sh
tenzir-ship release create v1.2.3 --title "Faster ingest"
tenzir-ship release publish v1.2.3
# GitHub release title: "Tenzir Ship v1.2.3: Faster ingest"
```

When the release has no title, `release create` leaves the manifest `title`
absent and GitHub receives `PROJECT VERSION` without the trailing `: TITLE`
segment:

```sh
tenzir-ship release create v1.2.3
tenzir-ship release publish v1.2.3
# GitHub release title: "Tenzir Ship v1.2.3"
```

This keeps the release manifest title focused on the release itself while
making GitHub release pages show the project and version more clearly. To
customize the GitHub title, pass a format string to `release publish --title`
or `Changelog.release_publish(title=...)`:

```sh
tenzir-ship release publish v1.2.3 --title '[$PROJECT $VERSION] $TITLE'
# GitHub release title: "[Tenzir Ship v1.2.3] Faster ingest"
```

The `$PROJECT`, `$VERSION`, and `$TITLE` variables are optional. A plain string
without variables overrides the GitHub title literally:

```sh
tenzir-ship release publish v1.2.3 --title "Faster ingest"
# GitHub release title: "Faster ingest"
```
