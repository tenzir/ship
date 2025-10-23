---
title: Show individual changelog entries
type: breaking
authors:
- mavam
- claude
created: 2025-10-22
pr: 1
---

Simplify viewing changelog entries with row numbers and a redesigned command structure.

The `show` command has been renamed to `list` for listing entries in table format,
and a new `show` command displays detailed entry views. The `list` command now includes
row numbers in a `#` column, making it easy to reference specific entries:

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

# Show entry by row number (simplest)
❯ tenzir-changelog show 2

# Show multiple entries
❯ tenzir-changelog show 1 2 5

# Show by entry ID (partial or full)
❯ tenzir-changelog show configure

# Show all entries from a release
❯ tenzir-changelog show v0.2.0
```

The detailed view displays metadata, release status, and formatted markdown body
with syntax highlighting in a unified panel layout.
