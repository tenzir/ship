---
title: Separate agent provenance from authorship
type: feature
authors:
  - mavam
agents:
  - codex
prs:
  - 44
components:
  - cli
  - python
created: 2026-08-10T10:22:35.591197Z
---

Changelog entries can now record coding tools with repeatable `--agent` flags and the Python `agents` parameter. Agent identifiers are stored separately from human authors, included in JSON exports, and omitted from rendered release notes.
