This release streamlines module mode by removing the multi-project feature in favor of the dedicated `modules` configuration. It removes the `--include-modules` flag (modules are now always included when configured) and enhances module mode to show released entries with version numbers. The release notes command now defaults to the latest release when no identifier is provided. Additionally, YAML frontmatter generation and error messages have been improved for better developer experience.

## 🔧 Changes

### Allow --markdown and --json to show all entries without identifiers

The `show` command's `--markdown` and `--json` export formats previously required at least one identifier argument. Now they work like the default table view and display all entries when no identifiers are specified.

*By @mavam and @claude.*
