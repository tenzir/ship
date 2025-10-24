---
title: Configure export style defaults
type: feature
authors:
- mavam
- codex
created: 2025-10-22
---

Allow setting the preferred release and export layout in config so compact notes
no longer need explicit flags.

Declare the preferred layout once in your project's `config.yaml`. Choose between
`standard` (the default sectioned notes) and `compact` (bullet lists with excerpts):

```yaml
export_style: compact
```

Then run:

```sh
tenzir-changelog --root changelog release vX.Y.Z --yes
```

The compact notes render automatically without passing the `--compact` flag. The
same default applies when exporting release notes:

```sh
tenzir-changelog --root changelog show -m vX.Y.Z
```
