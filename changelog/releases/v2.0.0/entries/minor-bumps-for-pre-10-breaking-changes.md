---
title: Minor bumps for pre-1.0 breaking changes
type: breaking
authors:
  - mavam
  - codex
prs:
  - 42
created: 2026-08-05T06:27:46.510211Z
---

Automatic release creation now keeps projects on major version zero when their unreleased entries include breaking changes. For example, a breaking entry after `v0.4.2` now produces `v0.5.0` instead of `v1.0.0`.

To declare the first stable release, request it explicitly:

```sh
tenzir-ship release create --major --yes
```

You can also pass `1.0.0` as the release version. Breaking entries continue to trigger major bumps after a project reaches `v1.0.0`. Active release candidates remain on their explicitly selected target during continuation and promotion. If multiple outstanding release-candidate series make that target ambiguous, `stats` warns and reports no next version instead of failing.
