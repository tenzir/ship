---
title: Aggregated module changelog summaries in release notes
type: feature
authors:
  - mavam
  - claude
created: 2025-12-19T09:16:57.667982Z
---

For projects with modules, parent releases now automatically include a summary
of module changes. Each parent release manifest records the module versions at
release time, enabling incremental tracking—subsequent releases only show new
module entries since the previous parent release.

Module summaries appear after the main changelog, separated by a horizontal
rule. Each module section shows its version and lists entries in compact format:
emoji prefix, title, and byline.
