---
title: Release candidate workflow
type: feature
authors:
  - mavam
  - codex
components:
  - cli
  - python
created: 2026-03-12T20:43:34.379484Z
---

`tenzir-ship` now supports release candidates via `release create --rc`. Creating a release candidate snapshots the current unreleased entries without consuming them, so you can iterate on `-rc.N` releases before promoting one to the final stable release. The stable base is inferred automatically, and rerunning the command continues the matching RC series when one already exists.

To ship the exact candidate as stable, use `tenzir-ship release create 1.2.3 --from v1.2.3-rc.2`. If you want to ignore existing release candidates and cut the stable release from the current unreleased queue instead, use `--current-unreleased`.

Publishing a release candidate now automatically creates a GitHub prerelease and prevents it from being marked as latest. Commands that resolve `latest`, including `release version`, `release publish`, and `show latest`, now default to the latest stable release rather than a release candidate. The bundled GitHub Actions release workflows also accept `rc`, `source-release`, and `current-unreleased` inputs so the RC lifecycle can be driven from CI as well as the CLI, while explicit `version` remains available only for exact overrides.
