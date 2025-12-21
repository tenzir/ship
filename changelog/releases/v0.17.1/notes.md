# Output Stream Fix

This release fixes a critical bug where status messages were written to stdout instead of stderr, breaking GitHub workflows and scripts that capture version output from commands like `release create`.

## 🐞 Bug fixes

### Correct output stream for status messages

Status messages now emit to stderr, allowing scripts to capture machine output from stdout without ANSI-colored status lines interfering.

Previously, commands like `release create` wrote both status messages and the version string to stdout, breaking workflows that capture output via `VERSION=$(uvx tenzir-changelog release create ...)`.

*By @mavam and @claude.*
