This release fixes bugs in changelog entry processing and version detection. The `authors` field now correctly normalizes single string values, and the `show` command no longer misidentifies entry IDs as release versions.

## 🐞 Bug fixes

### Fix authors field normalization when using a single string value

Changelog entries with `authors: "name"` (a single string) are now correctly normalized to a list. Previously, only the singular `author` key was normalized, which could cause rendering issues when `authors` was used with a string value.

*By @mavam and @claude.*

### Fix overly broad version string detection in show command

The `show` command no longer misidentifies changelog entry IDs as release versions. Previously, entries with IDs containing version-like patterns (e.g., `v1...`) were incorrectly treated as releases.

*By @mavam and @claude.*
