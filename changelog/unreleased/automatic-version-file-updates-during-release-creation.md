---
title: Automatic version file updates during release creation
type: feature
authors:
  - mavam
  - codex
pr: 10
created: 2026-02-28T21:09:43.473242Z
---

The release creation command now automatically updates version fields in package manifest files during release. When creating a release, `tenzir-ship` detects and updates `package.json`, `pyproject.toml`, `project.toml`, and `Cargo.toml` files in your project, including support for dynamic version files in monorepo workspaces.

You can control this behavior with the `release.version_bump_mode` configuration option in your `config.yaml`:

- `auto` (default): Automatically detect and update version files
- `off`: Skip version file updates

For more granular control, use the `release.version_files` option to explicitly specify which files to update. Auto-detection searches the project root and parent directory (for nested changelog projects) and gracefully skips files without static version fields.
