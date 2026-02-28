This release adds support for creating releases with only introductory text and no changelog entries, and splits the reusable release workflow into minimal and advanced variants. It also fixes changelog structure validation and release progress panel display issues.

## 🚀 Features

### Allow intro-only releases

Create releases with only introductory text and no changelog entries by using the `--intro` or `--intro-file` flags with `release create`. This is useful when re-publishing a package after yanking a previous artifact or retrying a failed publish workflow—scenarios where you want to create a new release version without adding changelog entries.

Previously, you had to provide at least one changelog entry to create a release. Now the release creation allows you to skip the entries entirely if you supply intro text. The `--intro` flag accepts text directly, while `--intro-file` reads from a Markdown file.

*By @mavam and @codex in #9.*

### Split reusable release workflow into minimal and advanced variants

`reusable-release.yaml` now acts as a minimal opinionated wrapper around a new `reusable-release-advanced.yaml` workflow.

The advanced workflow adds optional hooks and release controls for complex consumers: pre/post publish scripts, non-main `--no-latest` publishing, optional copy of release directories to `main`, `latest` branch updates, a `skip-publish` dry-run mode, and workflow outputs for `version` and `is_latest`.

*By @mavam and @codex.*

## 🐞 Bug fixes

### Enforce changelog structure for releases and command warnings

Release commands now validate changelog directory structure before they run and fail fast when it is invalid.

`release create` and `release publish` now stop with explicit errors when stray files or directories are detected (for example, an unexpected `changelog/next/` directory). Other commands (`show`, `add`, `stats`, and `release version`) emit warnings so layout problems are visible earlier, while `validate` reports full structural issues as regular validation errors.

*By @mavam and @codex.*

### Fix release progress panel truncating failed commands

When a release step fails, the full command now prints below the progress panel so you can copy-paste it for manual recovery.

Previously, long commands would get truncated in the release progress panel, making it difficult to reproduce the failure manually. Now when a step fails, the complete command is displayed in full below the panel, giving you what you need to debug and retry the operation.

*By @mavam and @claude in #7.*
