---
title: RC promotion includes entries added after the last candidate
type: bugfix
authors:
  - mavam
prs:
  - 28
created: 2026-06-10T16:28:31.963542Z
---

Promoting a release candidate to a stable release now folds in changelog entries added to `unreleased/` after the last candidate snapshot. The folded entries appear in the release manifest and notes, and are consumed from the unreleased queue. Previously they were silently left behind and missing from the stable release notes. The confirmation table now marks entries carried over from the candidate with a dim bullet and newly folded entries with a plus sign.
