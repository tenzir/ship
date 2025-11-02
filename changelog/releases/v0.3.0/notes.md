This release refines the workflow and exports, introduces numeric entry prefixes and emoji-styled types, and improves table layout and PR metadata.

## 💥 Breaking changes

### Assign numeric prefixes to changelog entries

Entry filenames now carry zero-padded numeric prefixes so they sort chronologically without relying on file metadata.

Existing unreleased files and archived release entries were renumbered to match the new scheme, updating manifest references as needed.

New entries start at `01` for each unreleased queue and expand past two digits automatically once you exceed 99 items, so identifiers stay compact without manual cleanup.

Release manifests now treat the `entries/` directory as the single source of truth, so the redundant `entries:` lists were removed and the version is implied by the directory name.

*By @codex.*

### Streamline entry browsing and setup

Promotes `tenzir-changelog show` as the single entry point for browsing changelog entries. The command defaults to the table view and adds quick transforms—`show -c` for cards, `show -m` for Markdown, and `show -j` for JSON—so reviewers can pivot between presentations without juggling subcommands. Markdown and JSON exports now accept row numbers, entry IDs, release versions, `unreleased`, or `-` to gather a curated bundle, and they respect `--compact/--no-compact` overrides on top of the configured default.

Release creation also shortens to `tenzir-changelog release <version> --yes`, and the old `--release` flag has been removed in favor of passing the version (or any other identifier) directly to `show`. Retires `tenzir-changelog bootstrap` in favor of an automatic setup path: the first `tenzir-changelog add` now creates `config.yaml`, prepares the required directories, and infers the project identifier so new repositories can capture entries immediately.

This is a breaking change for automation and documentation that previously relied on `tenzir-changelog bootstrap` or the separate `get/export` commands; update any scripts to call `show` and `release` with the new options. Running `tenzir-changelog` without arguments now opens the consolidated `show` view by default.

*By @codex.*

## 🚀 Features

### Configure export style defaults

Allow setting the preferred release and export layout in config so compact notes no longer need explicit flags.

Declare the preferred layout once in your project's `config.yaml`. Choose between `standard` (the default sectioned notes) and `compact` (bullet lists with excerpts):

```yaml
export_style: compact
```

Then run:

```sh
tenzir-changelog --root changelog release vX.Y.Z --yes
```

The compact notes render automatically without passing the `--compact` flag. The same default applies when exporting release notes:

```sh
tenzir-changelog --root changelog show -m vX.Y.Z
```

*By @mavam and @codex.*

### Highlight entry types with emoji styling

Adds a dedicated 💥 *Breaking changes* section ahead of other categories, switches feature highlights to 🚀, and keeps those emoji prefixed headings in Markdown and JSON exports unless you toggle them off with `--no-emoji`.

*By @codex.*

## 🔧 Changes

### Polish the table view layout

The default `tenzir-changelog show` table now adapts column widths to the active terminal, right-aligns row numbers, centers the version column, and inserts release separators so multi-digit identifiers stay readable even when the screen gets narrow.

*By @codex.*

### Refine compact Markdown exports

Compact Markdown exports now reuse the entry excerpt as the bullet text instead of repeating the title, keep author and PR bylines inline with GitHub handles prefixed by `@`, and end bullets with concise `(By … in #123)` annotations.

*By @codex.*

### Refine release workflow

Split the release command into dedicated `release create`, `release notes`, and `release publish` subcommands. Release creation now insists on `--yes` before mutating state, appends unreleased entries to an existing tag, keeps the manifest lean, remembers the chosen layout, and surfaces a dry-run summary. New `--patch`, `--minor`, and `--major` flags bump from the latest tagged release (respecting prefixes), while `release notes` re-exports any release (including `-`) and `release publish` pushes to GitHub via `gh`.

*By @codex.*

### Simplify PR metadata

Removes the legacy `pr` field from changelog exports and relies solely on the `prs` list.

*By @codex.*
