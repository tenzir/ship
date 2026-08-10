This release removes GitHub App token deprecation warnings from reusable release workflows while preserving existing App ID configurations.

## 🐞 Bug fixes

### GitHub App token input without deprecation warnings

The reusable release workflow no longer emits a deprecation warning when it generates a GitHub App token. Existing App IDs remain supported and require no configuration changes.

*By @mavam and @codex in #43.*
