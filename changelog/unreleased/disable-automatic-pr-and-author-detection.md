---
title: Disable automatic PR and author detection
type: feature
authors:
  - mavam
  - claude
components:
  - cli
created: 2025-12-30T08:45:43.796224Z
---

Add `omit_pr` and `omit_author` configuration options to prevent automatic inference of PR numbers and authors. When these config options are set to `true`, the `add` command will not auto-detect PR numbers from git branches or infer authors from git commits. If users explicitly provide `--pr` or `--author` flags while the corresponding omit option is enabled, a warning message is emitted and the value is ignored. This gives projects fine-grained control over changelog entry metadata.
