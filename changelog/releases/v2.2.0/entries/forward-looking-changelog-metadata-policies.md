---
title: Forward-looking changelog metadata policies
type: feature
authors:
  - mavam
prs:
  - 45
created: 2026-08-24T16:27:18.531396Z
---

Changelog projects can now enforce author and pull request metadata on unreleased entries without invalidating published releases.

Set `require_author: true` to require at least one author, or `omit_pr: true` to reject pull request numbers in unreleased entries:

```yaml
require_author: true
omit_pr: true
```

The `validate` command now applies `omit_pr` and `omit_author`, as well as the new requirements, only to unreleased entries by default. Previously, the omission policies also rejected metadata in released entries. Run `tenzir-ship validate --all-entries` to retain that full-history check and audit every release against the current policy.
