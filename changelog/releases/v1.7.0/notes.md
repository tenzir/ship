The reusable release workflow now works out of the box in external repositories without requiring Tenzir-org-specific secrets.

## 🔧 Changes

### Simplify reusable release workflow and decouple Tenzir org secrets

The reusable GitHub Actions release workflow now works in external repositories by default. It falls back to the caller repository's `GITHUB_TOKEN`, makes GitHub App authentication optional, and only enables GPG signing when a caller provides a signing key and opts into commit and/or tag signing. The single `release.yaml` workflow now also exposes the advanced hooks and release controls directly, including `skip-publish` for dry runs and smoke tests. Tenzir repositories can still opt into the existing bot identity, GitHub App token flow, and signed commits and tags by passing those settings explicitly.

*By @mavam and @codex.*
