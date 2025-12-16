---
title: Remove --include-modules flag from show command
type: breaking
authors:
- mavam
- claude
components:
- cli
created: 2025-12-15T16:10:28.91873Z
---

Remove the `--include-modules/--no-modules` flag from the `show` command. Modules are now always included when configured in the project. Use `--project <name>` to filter to a specific project if needed.

This simplifies the command interface and makes module discovery behavior more consistent. Previously, users had to explicitly use `--no-modules` to exclude module entries, which was unintuitive. Now, modules are included by default (when configured), and the standard `--project` filter can be used to focus on specific projects.

Also fixes a bug in card view (`show -c`) that caused "Row number X is out of range" errors when trying to access entries beyond the main project's count, as it was not including module entries in the row mapping.
