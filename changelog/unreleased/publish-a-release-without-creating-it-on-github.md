---
title: Publish a release without creating it on GitHub
type: feature
authors:
  - claude
  - codex
prs:
  - 41
created: 2026-08-04T08:30:19.785303Z
---

The new `--no-github-release` flag on `release publish` pushes the release tag without creating a GitHub release:

```sh
tenzir-ship release publish --commit --tag --no-github-release --yes
```

The flag requires `--tag`, so the command cannot report success without publishing either a tag or a GitHub release. The reusable workflow exposes the same choice as `create-github-release: false`. Use it when the release belongs in a different repository than the push target, or when it should appear only after downstream builds have proven the tag releasable. The `gh` CLI is not required when release creation is skipped.
