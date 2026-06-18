This release keeps package lockfiles in sync when release creation updates package manifest versions. It updates npm package-lock metadata and regenerates uv lockfile metadata so generated release commits stay consistent.

## 🚀 Features

### Package lockfile version updates

The `release create` command now keeps supported package lockfiles in sync when it updates package manifest versions.

When a sibling `package-lock.json` exists, `tenzir-ship` updates the lockfile root package version metadata alongside `package.json`, including already-current manifests with stale lockfiles. When a sibling `uv.lock` exists next to `pyproject.toml`, `tenzir-ship` runs `uv lock` after updating the manifest so uv regenerates the lockfile metadata. This keeps generated release commits consistent without requiring every workflow caller to add package-manager-specific post-create hooks.

*By @mavam and @codex in #30.*
