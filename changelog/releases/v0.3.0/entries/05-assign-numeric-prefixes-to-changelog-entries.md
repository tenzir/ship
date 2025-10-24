---
title: Assign numeric prefixes to changelog entries
type: breaking
authors:
- codex
created: 2025-10-23
---

Entry filenames now carry zero-padded numeric prefixes so they sort chronologically without relying on file metadata.

Existing unreleased files and archived release entries were renumbered to match the new scheme, updating manifest references as needed.

New entries start at `01` for each unreleased queue and expand past two digits automatically once you exceed 99 items, so identifiers stay compact without manual cleanup.

Release manifests now treat the `entries/` directory as the single source of truth, so the redundant `entries:` lists were removed and the version is implied by the directory name.
