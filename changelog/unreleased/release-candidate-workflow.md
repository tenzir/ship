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

When you are ready to ship the stable release, rerun `tenzir-ship release create` without `--rc` and the latest outstanding release candidate becomes the matching stable release automatically. Once an RC series exists, you either continue it with `release create --rc` or promote the latest candidate with the normal stable command.

Publishing a release candidate now automatically creates a GitHub prerelease and prevents it from being marked as latest. `release version` and `show latest` continue to resolve the latest stable release, while `release publish` without an explicit version now targets the latest release manifest, including RCs. The bundled GitHub Actions release workflows accept `rc` so you can keep creating RCs from CI, and the default stable workflow promotes the latest outstanding candidate automatically.
