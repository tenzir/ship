---
title: Show released entries and versions in module mode
type: feature
authors:
- mavam
- claude
components:
- cli
created: 2025-12-15T13:43:10.808926Z
---

Module mode (`show --module`) now displays released entries alongside unreleased ones, with their associated version numbers.

Previously, module mode would only show unreleased entries and hardcode the version column to "—". Now `iter_multi_project_entries()` collects both unreleased and released entries from each project, and `_render_entries_multi_project()` builds a release index per project to look up the actual version for each entry. This makes module mode consistent with single-project mode in terms of displayed content and metadata.
