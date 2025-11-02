---
title: Adopt package-aware project discovery
type: feature
authors:
- codex
- mavam
created: 2025-11-01
---

The new *package* concept allows for an alternate way of configuring a changelog
project. [Tenzir Packages](https://docs.tenzir.com/explanations/packages/) have
a top-level `package.yaml` file that contains the package configurtion. When a
changelog directory exists within a package directory, it is now possible to
omit the `changelog/config.yaml` configuration file. Instead, the changelog CLI
will take `id` and `name` from the `package.yaml` file.

This commit also has a few other drive-by improvements:

- On first use, the CLI now scaffolds the `changelog/` workspace implicitly, so
  `tenzir-changelog add` works from any directory even before the changelog tree
  exists.
- Interactive prompts now exit cleanly with an explicit error message when
  cancelled with Ctrl+C, avoiding confusing stack traces.
- New projects no longer sprout an empty `releases/` directory; we only create
  it once release manifests are generated.
