---
title: Automatic version updates for Tenzir package manifests
type: feature
authors:
  - mavam
components:
  - cli
prs:
  - 53
created: 2026-11-13T10:42:43.060173Z
---

The `release create` command now updates the `version` field in `package.yaml`, so Tenzir packages no longer need a manual version edit after each release.

In package mode, where the project reads its metadata from `package.yaml` next to the `changelog/` directory, a stable release writes the version as a quoted string without the `v` prefix:

```yaml
id: my-package
name: My Package
version: "0.2.0"
```

If `package.yaml` has no `version` key yet, the release adds one right after `name`. The update leaves comments, key order, multi-line descriptions, and nested `version` keys untouched. You can also list a `package.yaml` explicitly in `release.version_files`. Release candidates and `release.version_bump_mode: off` leave the file unchanged, as with the other version files.
