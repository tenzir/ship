---
title: Use folded YAML block for release descriptions
type: feature
authors:
- codex
- mavam
created: 2025-11-02
---

Release manifests now serialize the `description` field with a folded block
scalar (`>`) for readable multi-line wrapping instead of a single long scalar.
