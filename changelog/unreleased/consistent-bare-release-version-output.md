---
title: More robust release version normalization
type: bugfix
authors:
  - mavam
  - pi
components:
  - cli
  - python
created: 2026-03-11T19:14:56.715613Z
---

Release commands and the Python API now handle release versions more consistently when changelog data mixes tag-style versions such as `v1.2.3` with bare semantic versions such as `1.2.3`. This improves compatibility with existing changelog histories and makes release automation more reliable across commands that inspect, create, show, and publish releases.
