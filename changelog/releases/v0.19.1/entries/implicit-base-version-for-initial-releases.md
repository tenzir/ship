---
title: Implicit base version for initial releases
type: feature
authors:
  - mavam
  - claude
created: 2026-01-04T19:38:39.466209Z
---

When creating the first release, you can now use `--major`, `--minor`, or
`--patch` flags without an existing release. The tool uses an implicit `0.0.0`
as the base version:

- `--major` creates `1.0.0`
- `--minor` creates `0.1.0`
- `--patch` creates `0.0.1`

Previously, these flags required at least one prior release, forcing users to
always specify an explicit version for their first release.
