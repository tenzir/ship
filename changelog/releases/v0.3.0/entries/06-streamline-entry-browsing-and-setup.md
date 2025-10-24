---
title: Streamline entry browsing and setup
type: breaking
authors:
- codex
created: 2025-10-24
---

Promotes `tenzir-changelog show` as the single entry point for browsing changelog
entries. The command defaults to the table view and adds quick transforms—`show -c`
for cards, `show -m` for Markdown, and `show -j` for JSON—so reviewers can pivot
between presentations without juggling subcommands. Markdown and JSON exports now
accept row numbers, entry IDs, release versions, `unreleased`, or `-` to gather a
curated bundle, and they respect `--compact/--no-compact` overrides on top of the
configured default.

Release creation also shortens to `tenzir-changelog release <version> --yes`, and
the old `--release` flag has been removed in favor of passing the version (or any
other identifier) directly to `show`. Retires `tenzir-changelog bootstrap` in
favor of an automatic setup path: the first `tenzir-changelog add` now creates
`config.yaml`, prepares the required directories, and infers the project
identifier so new repositories can capture entries immediately.

This is a breaking change for automation and documentation that previously relied
on `tenzir-changelog bootstrap` or the separate `get/export` commands; update any
scripts to call `show` and `release` with the new options. Running
`tenzir-changelog` without arguments now opens the consolidated `show` view by
default.
