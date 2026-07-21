This release fixes changelog entry identity handling by scoping entry IDs to individual releases. Reused slugs now participate correctly in version bumps, validation, and changelog output.

## 🐞 Bug fixes

### Release-scoped changelog entry IDs

Release creation now treats changelog entry IDs as unique within each release instead of across the entire project history. Reusing a slug from an older release remains eligible for automatic version bumps, validation checks release-local references, and show output preserves every occurrence with its release context.

*By @mavam and @codex in #39.*
