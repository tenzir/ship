This release adds initial release support with implicit version bumping and fixes row numbering in multi-project views.

## 🚀 Features

### Implicit base version for initial releases

When creating the first release, you can now use `--major`, `--minor`, or `--patch` flags without an existing release. The tool uses an implicit `0.0.0` as the base version:

- `--major` creates `1.0.0`
- `--minor` creates `0.1.0`
- `--patch` creates `0.0.1`

Previously, these flags required at least one prior release, forcing users to always specify an explicit version for their first release.

*By @mavam and @claude.*

## 🐞 Bug fixes

### Correct row numbering in multi-project view

Row numbers in multi-project table view now count down from the newest entry, matching single-project behavior. The `show -c <row>` command also resolves row numbers correctly against the displayed table.

*By @mavam and @claude.*
