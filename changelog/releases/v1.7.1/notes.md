This release updates locked Python dependencies to patched upstream versions and aligns generated release commits with `v`-prefixed tags. It keeps release publishing, local development, and CI installs on maintained versions without changing normal `tenzir-ship` usage.

## 🐞 Bug fixes

### Patched locked Python dependencies

The repository's locked Python dependencies now use patched upstream releases, including fixes for the open security advisories reported by Dependabot.

This refresh keeps local development and CI installs on maintained versions without changing normal `tenzir-ship` usage.

*By @mavam and @codex.*

### Release commit messages matching v tags

The `release publish --commit` workflow now uses the tag-form version in generated release commits and annotated tag messages.

For example, publishing `v1.1.0` now creates `Release v1.1.0` instead of `Release 1.1.0`:

```sh
tenzir-ship release publish v1.1.0 --commit --tag --yes
```

This keeps generated release commits aligned with the corresponding Git tag and avoids mismatches in automation that expects the `v`-prefixed release identifier.

*By @mavam and @codex.*
