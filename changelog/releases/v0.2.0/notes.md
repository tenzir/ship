## 🚀 Features

- Add an optional compact export mode that renders bullet lists with bold titles and first-paragraph excerpts for Markdown and JSON outputs. (by @mavam and @codex)

## 🔧 Changes

- Render entry types with aligned emoji icons, and gate the project banner behind an opt-in `--banner` flag. (by @mavam and @codex)
- Entry files no longer store the project key; the CLI infers it from config. (by @mavam and @codex)
- Tighten the CLI entry table so IDs ellipsize instead of wrapping and adjust column widths to keep titles readable. (by @mavam and @codex)
- Ensure CLI views and exports stay reverse chronological by breaking same-day ties with entry file modification times. (by @mavam and @codex)
- Drop the workspace section from `config.yaml` in favor of top-level project metadata and update tooling, docs, and samples accordingly. (by @mavam and @codex)
- Entry parsing now converts `created` metadata to real dates and emits them for consumers. (by @mavam and @codex)
- Release manifests now keep metadata in `manifest.yaml`, store archived entries in `releases/<version>/entries/`, and write release notes to `notes.md` for consistent automation. (by @mavam and @codex)

## 🐞 Bug fixes

- When attempting to run `tenzir-changelog` outside a project root, you now get a helpful error message that's properly formatted. (by @mavam and @codex)
