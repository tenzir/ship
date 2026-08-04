Release publishing is now safer and more flexible: tenzir-ship confirms every commit, tag, and push before making changes, and it can publish a release tag without creating a GitHub release. Use the new option when another repository owns the release or downstream builds must validate the tag first.

## 🚀 Features

### Publish a release without creating it on GitHub

The new `--no-github-release` flag on `release publish` pushes the release tag without creating a GitHub release:

```sh
tenzir-ship release publish --commit --tag --no-github-release --yes
```

The flag requires `--tag`, so the command cannot report success without publishing either a tag or a GitHub release. The reusable workflow exposes the same choice as `create-github-release: false`. Use it when the release belongs in a different repository than the push target, or when it should appear only after downstream builds have proven the tag releasable. The `gh` CLI is not required when release creation is skipped.

*By @claude and @codex in #41.*

## 🐞 Bug fixes

### Confirm release publishing before mutating anything

`release publish` asked for confirmation only after the commit, tag, and both pushes had already reached the remote, so declining could not undo them. The prompt now appears before the first mutation and lists every step it is about to run.

*By @claude in #41.*
