---
title: Use slug-based entry naming
type: breaking
authors:
- claude
- mavam
prs:
- 3
component: cli
created: 2025-12-03T18:36:11Z
---

Entry files are now named using the slugified title (e.g., `my-feature.md`) instead of a numeric prefix (e.g., `01-my-feature.md`). This eliminates conflicts when multiple PRs create entries in parallel. The `created` field now stores a full UTC datetime for precise ordering within the same day.
