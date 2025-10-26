---
title: Invert show table order
type: breaking
authors:
- mavam
- claude
created: 2025-10-22
prs:
- 1
---

`tenzir-changelog show` now renders the primary changelog table with
backward-counting row numbers, so `#1` consistently targets the newest change
while older entries climb toward the top.

The command also subsumes the old `list`/`export` split: use the default view
for the numbered table, `-c/--card` for rich panels, or `-m/--markdown` /
`-j/--json` to export releases, the unreleased bucket, or ad-hoc selections.

```sh
# Browse every entry with numbered rows
uvx tenzir-changelog show

# Inspect a specific change as a card
uvx tenzir-changelog show -c 2

# Export an entire release (compact bullets optional)
uvx tenzir-changelog show -m v0.2.0
```

Cards highlight metadata, release status, and formatted Markdown together, so
you can review and share entry details without juggling multiple commands.
