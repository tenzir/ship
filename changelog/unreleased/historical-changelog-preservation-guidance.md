---
title: Changelog entry history guidance
type: change
authors:
  - mavam
  - codex
created: 2026-06-05T05:43:52.819816Z
---

The bundled agent skill now tells release automation to preserve published changelog history while still allowing clearly related unreleased entries to be merged before release.

Historical release notes, manifests, and released entry files are treated as immutable records, with edits reserved for explicit severe publication fixes. For unreleased work, agents now check whether a related entry already exists and merge it instead of creating duplicate changelog entries, reconciling the title, type, and description while appending distinct authors, pull request numbers, and components.

The merge guidance now requires a clear relationship based on the user-facing outcome, not just nearby implementation work, shared files, authors, or PR timing. Ambiguous changes should get a separate entry, and unrelated unreleased entries must remain untouched.
