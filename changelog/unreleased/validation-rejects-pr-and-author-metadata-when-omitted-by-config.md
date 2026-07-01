---
title: Validation rejects PR and author metadata when omitted by config
type: change
authors:
  - zedoraps
created: 2026-07-01T20:32:08.07749Z
---

The `validate` command now reports an error when an entry carries `prs` metadata while the config sets `omit_pr: true`, or `authors` metadata while the config sets `omit_author: true`. Previously, entries written directly to disk could bypass these options, which only guarded the `add` command.
