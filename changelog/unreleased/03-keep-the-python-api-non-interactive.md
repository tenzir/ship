---
title: Keep the Python API non-interactive
type: bugfix
authors:
- codex
- mavam
component: python
created: 2025-11-10
---

Using the `Changelog.add()` helper no longer triggers interactive prompts.

Automation that omits authors or entry types now completes without hanging and
uses safe defaults instead.
