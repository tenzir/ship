---
title: Consistent bare release version output
type: bugfix
authors:
  - mavam
  - pi
components:
  - cli
  - python
created: 2026-03-11T19:14:56.715613Z
---

The `release version` command and Python `Changelog.release_version()` now consistently return bare semantic versions such as `1.2.3`, even when older release manifests or directories still use `v`-prefixed names. Git tags and GitHub releases continue to use tags such as `v1.2.3`.
