---
title: Release candidate promotion accepts edited entries
type: change
authors:
  - IyeOnline
prs:
  - 48
created: 2026-10-26T16:07:42.835188Z
---

Promoting a release candidate to a stable release no longer fails when an entry from the candidate snapshot was edited in `unreleased/` afterwards. The stable release now uses the edited entry content, just like a follow-up release candidate would.
