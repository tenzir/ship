---
title: Decouple reusable release workflow from Tenzir org secrets
type: change
authors:
  - mavam
  - pi
created: 2026-03-12T07:58:22Z
---

The reusable GitHub Actions release workflows now work in external repositories by default. They fall back to the caller repository's `GITHUB_TOKEN`, make GitHub App authentication optional, and only enable GPG signing when a caller provides a signing key. The thin `reusable-release.yaml` wrapper preserves inherited caller secrets for secret-backed hook scripts and now exposes `skip-publish` for dry runs and smoke tests. Tenzir repositories can still opt into the existing bot identity, GitHub App token flow, and signed commits and tags by passing those settings explicitly.
