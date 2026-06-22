This release improves changelog entry guidance so agents avoid premature pull request metadata and rely on automatic pull request inference until a number exists.

## 🐞 Bug fixes

### PR metadata guidance for changelog entries

The changelog-entry skill no longer suggests passing `--pr` in the default `tenzir-ship add` command before a pull request number exists. Agents can rely on PR auto-inference once a pull request is open, or backfill `prs` after filing the PR.

*By @mavam and @codex in #31.*
