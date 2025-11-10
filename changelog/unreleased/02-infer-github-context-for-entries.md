---
title: Infer GitHub context for entries
type: feature
authors:
- codex
- mavam
component: cli
created: 2025-11-10
---

`tenzir-changelog add` now reads your local `gh` login and the active pull
request to auto-populate `authors` and `prs`, so you can skip passing `--author`
and `--pr` when the data already exists.
