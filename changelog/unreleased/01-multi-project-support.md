---
title: Support multi-project changelog operations
type: feature
author: claude
created: 2025-10-29
---

Adds support for managing changelogs across multiple projects with a single command. You can now use multiple `--root` flags to operate on multiple changelog projects simultaneously.

The `show` command displays entries from all projects in a unified table with a Project column, making it easy to see unreleased changes across your entire product ecosystem.

The `show` command with markdown or JSON export (`-m` or `-j`) groups entries by project, following a hierarchical format: version → project → entry type → entries.

Table filtering works equally well across multiple projects: `--project` and `--component` constraints are honored, duplicate entry identifiers stay mapped to their original project, and `tenzir-changelog show <version>` returns the coordinated release rows across all roots.

The `release create` command with multiple roots performs coordinated release creation, atomically creating the same version across all projects and moving unreleased entries to releases in each project. Run it without `--yes` for a dry run that previews the release entry counts before you ship.

This feature enables teams with multi-repo or monorepo architectures to maintain coordinated releases with unified changelog documentation.
