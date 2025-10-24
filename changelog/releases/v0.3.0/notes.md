## 💥 Breaking changes

- Entry filenames now carry zero-padded numeric prefixes so they sort chronologically without relying on file metadata. (by @codex)
- Promotes `tenzir-changelog show` as the single entry point for browsing changelog entries. The command defaults to the table view and adds quick transforms—`show -c` for cards, `show -m` for Markdown, and `show -j` for JSON—so reviewers can pivot between presentations without juggling subcommands. Markdown and JSON exports now accept row numbers, entry IDs, release versions, `unreleased`, or `-` to gather a curated bundle, and they respect `--compact/--no-compact` overrides on top of the configured default. (by @codex)

## 🚀 Features

- Allow setting the preferred release and export layout in config so compact notes no longer need explicit flags. (by @mavam and @codex)
- Adds a dedicated 💥 *Breaking changes* section ahead of other categories, switches feature highlights to 🚀, and keeps those emoji prefixed headings in Markdown and JSON exports unless you toggle them off with `--no-emoji`. (by @codex)

## 🔧 Changes

- The default `tenzir-changelog show` table now adapts column widths to the active terminal, right-aligns row numbers, centers the version column, and inserts release separators so multi-digit identifiers stay readable even when the screen gets narrow. (by @codex)
- Compact Markdown exports now reuse the entry excerpt as the bullet text instead of repeating the title, keep author and PR bylines inline with GitHub handles prefixed by `@`, and end bullets with concise `(By … in #123)` annotations. (by @codex)
- Split the release command into dedicated `release create`, `release notes`, and `release publish` subcommands. Release creation now insists on `--yes` before mutating state, appends unreleased entries to an existing tag, keeps the manifest lean, remembers the chosen layout, and surfaces a dry-run summary. New `--patch`, `--minor`, and `--major` flags bump from the latest tagged release (respecting prefixes), while `release notes` re-exports any release (including `-`) and `release publish` pushes to GitHub via `gh`. (by @codex)
- Removes the legacy `pr` field from changelog exports and relies solely on the `prs` list. (by @codex)
