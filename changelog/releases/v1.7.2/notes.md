This patch release removes the Node 20 deprecation warning from the reusable release workflow when it generates GitHub App tokens on GitHub-hosted runners. Repositories that call the shared release workflow now get clean release logs without extra configuration.

## 🐞 Bug fixes

### Node 24 GitHub App tokens in reusable workflows

The reusable release workflow no longer emits the Node 20 deprecation warning when it generates GitHub App tokens on GitHub-hosted runners.

Repositories that call `tenzir/ship/.github/workflows/release.yaml` now get clean release logs without extra configuration.

*By @mavam and @codex.*
