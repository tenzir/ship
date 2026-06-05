---
title: Changelog entry history guidance
type: change
authors:
  - mavam
  - codex
created: 2026-06-05T05:43:52.819816Z
---

The bundled agent skill now tells release automation to preserve published changelog history while still allowing related unreleased entries to be merged before release.

Historical release notes, manifests, and released entry files are treated as immutable records, with edits reserved for explicit severe publication fixes. For unreleased work, agents now check whether a related entry already exists and merge it instead of creating duplicate changelog entries, reconciling the title, type, and description while appending distinct authors, pull request numbers, and components.
