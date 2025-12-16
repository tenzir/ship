This release streamlines module mode by removing the multi-project feature in favor of the dedicated `modules` configuration. It removes the `--include-modules` flag (modules are now always included when configured) and enhances module mode to show released entries with version numbers. The release notes command now defaults to the latest release when no identifier is provided. Additionally, YAML frontmatter generation and error messages have been improved for better developer experience.

## 💥 Breaking changes

### Remove --include-modules flag from show command

**Components:** `cli`

Remove the `--include-modules/--no-modules` flag from the `show` command. Modules are now always included when configured in the project. Use `--project <name>` to filter to a specific project if needed.

This simplifies the command interface and makes module discovery behavior more consistent. Previously, users had to explicitly use `--no-modules` to exclude module entries, which was unintuitive. Now, modules are included by default (when configured), and the standard `--project` filter can be used to focus on specific projects.

Also fixes a bug in card view (`show -c`) that caused "Row number X is out of range" errors when trying to access entries beyond the main project's count, as it was not including module entries in the row mapping.

*By @mavam and @claude.*

### Remove multi-project mode

**Components:** `cli`

Remove the multi-project mode feature that allowed specifying multiple `--root` flags to coordinate releases across projects.

Users who need monorepo support should use the `modules` feature instead, which was designed for this purpose and remains fully supported.

**Migration guide:**

- Replace `--root proj1 --root proj2 --root proj3` with `modules` configuration in `config.yaml`
- Single `--root` path continues to work as before
- The Python API now accepts a single `root` parameter instead of `roots` sequence

*By @mavam and @claude.*

## 🚀 Features

### Default to latest release in release notes command

**Components:** `cli`

Make the `release notes` command show the latest release by default when no identifier is provided. Previously, an explicit version identifier was required. Now omitting the identifier automatically resolves to the latest available release, streamlining the common case of viewing current release notes.

*By @mavam and @claude.*

### Show released entries and versions in module mode

**Components:** `cli`

Module mode (`show --module`) now displays released entries alongside unreleased ones, with their associated version numbers.

Previously, module mode would only show unreleased entries and hardcode the version column to "—". Now `iter_multi_project_entries()` collects both unreleased and released entries from each project, and `_render_entries_multi_project()` builds a release index per project to look up the actual version for each entry. This makes module mode consistent with single-project mode in terms of displayed content and metadata.

*By @mavam and @claude.*

## 🔧 Changes

### Fix YAML list indentation in entry frontmatter

**Components:** `python`

Generated changelog entries now use standard YAML indentation with 2 spaces for list items under keys like `authors:` and `components:`.

*By @mavam and @claude.*

### Improve YAML parsing error messages

**Components:** `cli`

Improve error messages when YAML frontmatter parsing fails in changelog entries. The error message now indicates which file has the problem and suggests to quote strings containing colons.

*By @mavam and @claude.*
