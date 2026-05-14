This release validates changelog entry metadata and release manifests with JSON Schema. It reports malformed fields such as non-numeric pull request references instead of silently accepting invalid changelog data.

## 🐞 Bug fixes

### Schema-backed changelog validation

Validate changelog entry metadata and release manifests with JSON Schema so malformed fields such as non-numeric pull request references are reported instead of silently passing validation.

*By @mavam and @codex in #26.*
