---
title: Fix logging when outside project root
type: bugfix
projects:
- changelog
authors:
- mavam
created: '2025-10-21'
---

When attempting to run `tenzir-changelog` outside a project root, you now get a
helpful error message that's properly formatted.
