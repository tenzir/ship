---
title: Forward-looking changelog metadata policies
type: feature
authors:
  - mavam
prs:
  - 45
created: 2026-08-24T16:27:18.531396Z
---

Changelog projects can now enforce author and pull request metadata on new entries without invalidating published releases.

Set `require_author: true` to require at least one author, or `omit_pr: true` to reject pull request numbers in unreleased entries:

```yaml
require_author: true
omit_pr: true
```

The `validate` command applies these policies to unreleased entries by default. Run `tenzir-ship validate --all-entries` when you want to audit released entries against the current policy as well.
