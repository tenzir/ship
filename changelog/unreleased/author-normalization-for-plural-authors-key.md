---
title: Fix authors field normalization when using a single string value
type: bugfix
authors:
  - mavam
  - claude
created: 2026-01-26T19:07:13.751223Z
---

Changelog entries with `authors: "name"` (a single string) are now correctly normalized to a list. Previously, only the singular `author` key was normalized, which could cause rendering issues when `authors` was used with a string value.
