---
title: Unified show command replaces release notes
type: breaking
authors:
  - mavam
  - claude
created: 2026-01-07T13:22:33.991861Z
---

The `release notes` command has been removed and replaced by the unified `show`
command with new `--release`, `--all`, and `--released-only` flags.

Previously, the CLI had two overlapping commands with different mental models:
`show` displayed entries in a flat list, while `release notes` formatted them
as release documents. This caused confusion because both produced similar JSON
output for single releases but had different defaults and use cases.

The new design follows a single principle: **selection is always entry-centric,
and `--release` is a display modifier**. Version identifiers like `v1.0.0` mean
"entries from release v1.0.0", and the `--release` flag changes how those
entries are presented—grouped by release with full metadata—rather than what
gets selected.

**Migration guide**:

| Old command                   | New command                    |
| ----------------------------- | ------------------------------ |
| `release notes v1.0.0`        | `show v1.0.0 --release -m`     |
| `release notes v1.0.0 --json` | `show v1.0.0 --release --json` |
| `release notes -`             | `show --release -m`            |
| `release notes - --json`      | `show --release --json`        |

**New capabilities**: The `--all` flag enables batch export of all releases in a
single invocation.

```bash
# Export all releases as JSON (new)
tenzir-changelog show --all --release --json

# Export only released versions, excluding unreleased
tenzir-changelog show --all --release --released-only --json
```

This is particularly valuable for documentation sync scripts that previously
required invoking the tool once per release. With ~320 releases across 7
projects, the sync time drops from ~2 minutes to ~2-3 seconds.

**JSON output consistency**: With `--release`, JSON output is always an array of
release objects, even for a single release. This ensures deterministic parsing
in scripts.

```json
[
  {
    "version": "v1.0.0",
    "title": "Release Title",
    "intro": "Release introduction...",
    "entries": [...]
  }
]
```

Without `--release`, JSON remains a single object with a flat `entries` array.
