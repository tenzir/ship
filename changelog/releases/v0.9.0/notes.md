## 💥 Breaking changes

### Use slug-based entry naming

**Component:** `cli`

Entry files are now named using the slugified title (e.g., `my-feature.md`) instead of a numeric prefix (e.g., `01-my-feature.md`). This eliminates conflicts when multiple PRs create entries in parallel. The `created` field now stores a full UTC datetime for precise ordering within the same day.

*By @claude and @mavam in [#3](https://github.com/tenzir/changelog/pull/3).*

## 🚀 Features

### Automatically detect changelog/ subdirectory as root

**Component:** `cli`

The CLI now automatically uses a `changelog/` subdirectory as the project root when running commands from the parent directory. This means you no longer need to pass `--root changelog` when the current directory contains a valid changelog project in a `changelog/` subdirectory.

*By @claude and @mavam in [#4](https://github.com/tenzir/changelog/pull/4).*

### Support singular pr and author keys

**Component:** `cli`

Changelog entries can now use the singular `pr` and `author` keys in YAML frontmatter as shorthand for single values. For example, instead of writing:

```yaml
prs:
  - 42
authors:
  - codex
```

You can now write:

```yaml
pr: 42
author: codex
```

Both forms are supported, and the singular form is automatically normalized to the plural form when the entry is read. Using both forms in the same entry is an error.

*By @claude and @mavam in [#2](https://github.com/tenzir/changelog/pull/2).*

## 🔧 Changes

### Highlight inferred GitHub identities

**Component:** `cli`

GitHub login and pull request detection logs now render the inferred identifiers in bold so they stand out without relying on prefixed punctuation.

*By @codex and @mavam.*
