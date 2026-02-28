---
title: Allow intro-only releases
type: feature
authors:
  - mavam
  - codex
pr: 9
created: 2026-02-28T10:39:48.110043Z
---

Create releases with only introductory text and no changelog entries by using the `--intro` or `--intro-file` flags with `release create`. This is useful when re-publishing a package after yanking a previous artifact or retrying a failed publish workflow—scenarios where you want to create a new release version without adding changelog entries.

Previously, you had to provide at least one changelog entry to create a release. Now the release creation allows you to skip the entries entirely if you supply intro text. The `--intro` flag accepts text directly, while `--intro-file` reads from a Markdown file.
