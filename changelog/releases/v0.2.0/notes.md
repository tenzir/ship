This release improves table and export layouts, simplifies configuration, and streamlines the release archive while fixing logging and ordering.

## 🚀 Features

### Compact export output

Add an optional compact export mode that renders bullet lists with bold titles and first-paragraph excerpts for Markdown and JSON outputs.

*By @mavam and @codex.*

## 🔧 Changes

### Center type column emoji labels

Render entry types with aligned emoji icons, and gate the project banner behind an opt-in `--banner` flag.

*By @mavam and @codex.*

### Drop implicit project metadata

Entry files no longer store the project key; the CLI infers it from config.

*By @mavam and @codex.*

### Improve entry table layout

Tighten the CLI entry table so IDs ellipsize instead of wrapping and adjust column widths to keep titles readable.

*By @mavam and @codex.*

### Order same-day entries by modification time

Ensure CLI views and exports stay reverse chronological by breaking same-day ties with entry file modification times.

*By @mavam and @codex.*

### Simplify changelog configuration

Drop the workspace section from `config.yaml` in favor of top-level project metadata and update tooling, docs, and samples accordingly.

*By @mavam and @codex.*

### Store entry creation dates as Date objects

Entry parsing now converts `created` metadata to real dates and emits them for consumers.

*By @mavam and @codex.*

### Streamline release archive layout

Release manifests now keep metadata in `manifest.yaml`, store archived entries in `releases/<version>/entries/`, and write release notes to `notes.md` for consistent automation.

*By @mavam and @codex.*

## 🐞 Bug fixes

### Fix logging when outside project root

When attempting to run `tenzir-changelog` outside a project root, you now get a helpful error message that's properly formatted.

*By @mavam and @codex.*
