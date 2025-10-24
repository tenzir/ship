---
title: Get individual changelog entries
type: breaking
authors:
- mavam
- claude
created: 2025-10-22
prs:
- 1
---

Simplify viewing changelog entries with row numbers and a redesigned command structure.

The `list` command renders tabular views with a `#` column so you can reference specific entries,
and the new `get` command displays detailed entry views. Together they streamline browsing changes:

```sh
# List all entries with row numbers
❯ tenzir-changelog list
┏━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━┓
┃ # ┃ Date       ┃ Version ┃ Title           ┃ Type ┃
┡━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━┩
│ 1 │ 2025-10-22 │ —       │ Configure exp…  │  🌟  │
│ 2 │ 2025-10-22 │ —       │ Show individ…   │  🌟  │
│ 3 │ 2025-10-21 │ v0.2.0  │ Streamline r…   │  🔧  │
└───┴────────────┴─────────┴─────────────────┴──────┘

# Get entry by row number (simplest)
❯ tenzir-changelog get 2

# Get multiple entries
❯ tenzir-changelog get 1 2 5

# Get by entry ID (partial or full)
❯ tenzir-changelog get configure

# Get all entries from a release
❯ tenzir-changelog get v0.2.0
```

The detailed view displays metadata, release status, and formatted markdown body
with syntax highlighting in a unified panel layout.
