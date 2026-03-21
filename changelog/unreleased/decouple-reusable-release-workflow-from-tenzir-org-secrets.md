---
title: Decouple reusable release workflow from Tenzir org secrets
type: change
authors:
  - mavam
  - pi
created: 2026-03-12T07:58:22Z
---

The reusable GitHub Actions release workflow now works in external repositories
by default. It falls back to the caller repository's `GITHUB_TOKEN`, makes
GitHub App authentication optional, only uses `push_token` when a caller opts
into it explicitly, and only enables GPG signing when a caller provides a
signing key. Callers now also pass the workflow-source repository/ref
explicitly, so the workflow installs the intended `tenzir-ship` revision
instead of inferring it from the caller context. The release hooks and publish
controls now live directly on `reusable-release.yaml`, and the separate
`reusable-release-advanced.yaml` entrypoint has been removed. Tenzir
repositories can still opt into the existing bot identity, explicit push-token
auth, GitHub App token flow, and signed commits and tags by passing those
settings explicitly.
