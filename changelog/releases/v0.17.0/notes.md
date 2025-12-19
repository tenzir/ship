# Machine-Readable Release Output

This is the first stable release of the Tenzir Claude Marketplace, a collection of plugins that extend Claude Code's capabilities for working with the Tenzir ecosystem.

This release introduces fully qualified skill names across all plugins for clarity and consistency. The `writing` plugin has been renamed to `prose` to better reflect its purpose, and the auto-update plugin has been removed in favor of manual updates. The CI now validates all skills using the official Agent Skills specification.

## 🚀 Features

### Machine-readable version output from release create

The `release create` command now outputs the created version to stdout, enabling shell scripting patterns like `VERSION=$(tenzir-changelog release create --minor --yes)`. All Rich output (tables, panels) now goes to stderr, keeping stdout clean for machine-readable results.

*By @mavam and @claude.*
