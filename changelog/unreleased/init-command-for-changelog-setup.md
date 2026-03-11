---
title: Init command for changelog setup
type: feature
authors:
  - mavam
  - pi
created: 2026-03-11T16:52:46.813421Z
---

A new `init` command allows for scaffolding a new changelog project interactively or with the `--yes` flag. It supports both standalone and package modes, and prevents accidental overwriting of existing projects.

```sh
tenzir-ship init
```

This reduces the manual effort required to set up a new changelog.
