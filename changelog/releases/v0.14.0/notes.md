This release adds H1 headings to release notes output, making documents more structured and easier to navigate.

## 🚀 Features

### H1 heading in release notes based on manifest title

Release notes now include an H1 heading at the top of the document. The heading is derived from the manifest `title` field:

- **Custom title**: If a title is set and differs from the default format, it's used directly (e.g., `# Big Release`)
- **Default**: Otherwise, the heading uses `{project_name} {version}` (e.g., `# Tenzir Changelog v1.0.0`)

This applies to all release notes generation: `notes.md` files created during releases, the `release notes` command output, and markdown exports via `show --markdown`.

*By @mavam and @claude.*
