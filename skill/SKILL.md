---
name: tenzir-ship
description: Use when adding changelog entries, creating release notes, cutting releases, and publishing them to GitHub.
---

# tenzir-ship

This skill bundles key release engineering use cases with tenzir-ship.

## Determine version bump

Begin with determining the version of the release. Run:

```sh
uvx tenzir-ship stats
```

This will display the next version based on the unreleased changelog entry types
as follows:

- Patch (x.y.Z): `bugfix`
- Minor (x.Y.0): `change` or `feature`
- Major (X.0.0): `breaking`

Cutting a release without changelog entries requires manual specification of the
version bump.

## Use Cases

### Add a changelog entry

Add changelog entries as part of shipping bugfixes, changes, and features during
day-to-day development.

Instructions: `references/add-changelog-entry.md`

## Trigger a GitHub Actions release workflow

Cut a release by invoking an existing GitHub Actions workflow that performs
release operations end-to-end.

Instructions: `references/trigger-github-actions-release.md`

## Create a local release and publish to GitHub

A local release involves a two-phase process:

1. Cut a local in-tree release: `references/create-standard-release.md`
2. Publish the release to GitHub: `references/publish-release.md`

## Create a module release

Changelog projects may contain modules (per the output of `stats`). This
involves first cutting a release for each module and then the parent project.

Instructions: `references/create-module-release.md`

## Documentation

When running into errors during the release process, obtain additional help
by reading the official documentation:

- https://docs.tenzir.com/reference/ship-framework.md
- https://docs.tenzir.com/guides/packages/maintain-a-changelog.md
