---
title: Split reusable release workflow into minimal and advanced variants
type: feature
authors:
  - mavam
  - codex
created: 2026-02-16T15:47:58Z
---

`reusable-release.yaml` now acts as a minimal opinionated wrapper around a new
`reusable-release-advanced.yaml` workflow.

The advanced workflow adds optional hooks and release controls for complex
consumers: pre/post publish scripts, non-main `--no-latest` publishing,
optional copy of release directories to `main`, `latest` branch updates, and
workflow outputs for `version` and `is_latest`.
