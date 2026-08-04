---
title: Publish a release without creating it on GitHub
type: feature
authors:
  - claude
prs:
  - 41
created: 2026-08-04T08:30:19.785303Z
---

The new `--no-github-release` flag on `release publish` stops after the tag is pushed, and the reusable workflow exposes it as `create-github-release`. Use it when the release belongs in a different repository than the push target, or when it should only appear once downstream builds have proven the tag releasable. The `gh` CLI is no longer required when the step is skipped.
