---
title: Agent skill respects PR and author omission options
type: change
authors:
  - zedoraps
prs:
  - 33
created: 2026-07-01T20:44:24.83769Z
---

The `tenzir-ship` agent skill no longer instructs agents to record PR numbers or authors in projects whose config sets `omit_pr: true` or `omit_author: true`, and now runs `tenzir-ship validate` after creating or editing an entry. Previously, the skill's guidance to manually write PR numbers into entry frontmatter bypassed these options.
