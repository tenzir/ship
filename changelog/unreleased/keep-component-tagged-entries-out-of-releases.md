---
title: Keep component-tagged entries out of releases
type: feature
authors:
  - IyeOnline
components:
  - cli
  - python
created: 2026-11-16T13:44:12.932542Z
---

The new `release.exclude_components` config option keeps entries tagged with any of the listed components out of `release create`. Those entries stay in `unreleased/`, do not affect the automatic version bump, and are left out of release candidates and their promotion:

```yaml
components:
  node: Applies only to the v6 line.
release:
  exclude_components: [node]
```

Pass `--exclude-component <label>` to `release create`, or `exclude_components` to the Python API, to replace the configured list for one release. `stats` applies the configured list when it reports the next version.
