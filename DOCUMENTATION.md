# Tenzir Changelog CLI

`tenzir-changelog` is a reusable command-line interface for curating changelog
entries, shipping release notes, and assembling the public changelog across
Tenzir repositories. Teams can run it directly from PyPI with
[`uv`](https://docs.astral.sh/uv/) so that contributors, automation, and docs
pipelines all share the same workflow.

## Prerequisites

- Python 3.12 or newer
- `uv` installed locally
- Access to the repository that hosts the changelog files; the CLI reads and
  writes within the current working tree
- (Optional) A GitHub token with `repo` scope exported as
  `GITHUB_TOKEN` for private repository inspection and PR metadata lookups

## Quick Start

1. Create your first changelog entry (this also scaffolds the project):
   ```sh
   uvx tenzir-changelog add --title "Initial setup" --type change --description "Track changelog work."
   ```
   The first invocation writes `config.yaml`, prepares `unreleased/` and
   `releases/`, and infers sensible defaults from the directory name—no
   separate bootstrap step required.
2. View the current changelog for your working tree:
   ```sh
   uvx tenzir-changelog show
   ```
   The default table lists every entry with row numbers, making it easy to
   reference specific items. Inspect a card layout with
   `uvx tenzir-changelog show -c 1` or export a release via
   `uvx tenzir-changelog show -m v0.2.0`.
3. Add entries as you prepare pull requests:
   ```sh
   uvx tenzir-changelog add --title "Introduce pipeline builder" --type feature --pr 101
   ```
   Pass flags for authors, projects, and descriptions to avoid interactive
   prompts, or let the CLI discover metadata automatically.

## CLI Overview

`tenzir-changelog` offers a focused set of commands. All commands accept
`--config` to point at an explicit configuration file (YAML format, defaulting
to `config.yaml`) and `--root` to operate on another repository.

- **`tenzir-changelog show [identifiers...]`**
  Display changelog entries in multiple views. With no flags it renders a rich
  table of entries, accepting row numbers, entry IDs (full or partial), release
  versions, and the tokens `unreleased` or `-` to target pending entries.
  - Table view (default) mirrors the old `list` command. Pass `--project`
    or `--banner` to filter or augment the table output.
    Supply a release version (e.g., `v1.0.0`) as an identifier to focus on a specific manifest.
  - `-c/--card` shows detailed cards for each matching entry; at least one
    identifier is required.
  - `-m/--markdown` exports a release, the unreleased bucket, or specific entries as Markdown.
  - `-j/--json` exports a release, the unreleased bucket, or specific entries as JSON.
  - `--compact`/`--no-compact` toggles the compact export layout for Markdown
    and JSON, defaulting to the project's `export_style`.
  - `--no-emoji` removes type emoji from the output (where supported).
  - Supply multiple identifiers to target a mix of rows, entry IDs, releases, or `unreleased`—the CLI deduplicates them before formatting.

- **`tenzir-changelog add`**
Create a new change entry in `unreleased/`. Highlights:
  - Prompts for change type (`breaking`, `feature`, `bugfix`, `change`) with one-key shortcuts
    (`0`, `1`, `2`, `3`), the project, summary, and detailed notes
  - Auto-detects authors, PR number, title, and body via `gh` or the GitHub API
    (requires `GITHUB_TOKEN` when the repository is private)
  - Supports `--web` mode to open a prefilled GitHub file creation URL for
    contributors without local write access
  - Enforces naming conventions, validates required frontmatter, and can append
    changelog fragments to an existing draft entry
  - Assigns globally sequential filenames with two-digit numeric prefixes,
    e.g., `01-improve-help-formatting.md`, automatically widening once more than
    99 entries exist so lexicographic order matches the changelog chronology even
    after edits

- **`tenzir-changelog release <version>`**
  Assemble a release under `releases/` by moving every unused entry file into
  `releases/<version>/entries/` and writing release metadata to
  `manifest.yaml` (containing the release date and optional intro). Markdown
  notes render in `notes.md`, while the entry directory is now the single
  source of truth for which fragments shipped in the release. Accepts options
  for release title, version, description, release date, and the `--compact`
  flag to emit bullet-point notes. You can supply additional narrative via
  `--intro-file`, and the CLI prints the manifest path plus a summary of
  included entries.

- **`tenzir-changelog validate`**
  Run structural checks across entry files, release manifests, and exported
  documentation. The validator reports missing metadata, unused entries,
  duplicate entry IDs, and configuration drift across repositories.

## Configuration Concepts

- **Project:** Identifies which documentation stream the changelog belongs to.
  Every entry and release references the same project string.
- **Entry:** A changelog consists of a set of entries. Each entry uses one of
  four hard-coded types—`breaking`, `feature`, `bugfix`, or `change`.
- **Configuration File:** Settings live in `config.yaml` by default. The file
  captures repository metadata, the single project name, GitHub repository
  slugs, and any other instance-specific options (such as preferred intro
  templates or asset directories) so commands like `add` and `release`
  can infer context without repeated flags. All options sit at the top level
  (`id`, `name`, `description`, `repository`, `intro_template`,
  `assets_dir`, `export_style`), making the configuration easy to read and diff. The `id`
  serves as the canonical slug written into entry metadata, while `name`
  provides the human-friendly label surfaced in release titles and CLI output.
  Set `export_style` to `compact` to prefer the bullet-list layout for release
  notes and `tenzir-changelog show -m` without passing `--compact`
  each time.
- **Repositories:** A project may pull changelog entries from other repositories
  (e.g., satellites or private modules). Configuration entries include the
  repository slug, Git remote URL, and branch-to-track for releases.

## Example Workflows

- **First-time setup:**  
  Run `uvx tenzir-changelog show` in any repository to confirm the CLI sees
  your changelog project, and rely on `uvx tenzir-changelog add` to create the
  scaffold automatically on first use.

- **Daily development:**  
  Developers run `uvx tenzir-changelog add` while preparing pull requests to
  capture changes. CI pipelines can enforce `uvx tenzir-changelog validate` to
  guarantee metadata completeness.

- **Cutting a release:**  
  Maintainers execute `uvx tenzir-changelog release v5.4.0`, supply the
  introductory notes (or reference a Markdown file with richer content and
  imagery), and review the generated manifest before handing it off to docs.
  The command pulls the project display name from `config.yaml`, so no extra switches
  are required.

## Tutorial

This walkthrough mirrors the dogfooded project under `changelog/` and shows
how to initialize a repository, add entries, preview the backlog, and publish a
release manifest with richer introductory material. All commands run from the
project root.

1. **Create a sandbox:**  
   ```sh
   mkdir my-changelog
   cd my-changelog
   uvx tenzir-changelog add \
     --title "Add pipeline builder" \
     --type feature \
     --description "Introduces the new pipeline builder UI." \
     --author alice \
     --pr 101
   ```
   The first `add` invocation scaffolds the project automatically—no manual
   config editing needed. After the command completes, inspect `config.yaml`:
   ```yaml
   id: my-changelog
   name: My Changelog
   ```

2. **Capture entries:**  
   Record additional representative changes with authors and pull-request numbers:
   ```sh
   uvx tenzir-changelog add \
     --title "Fix ingest crash" \
     --type bugfix \
     --description "Resolves ingest worker crash when tokens expire." \
     --author bob \
     --pr 102 \
     --pr 115

   uvx tenzir-changelog add \
     --title "Improve CLI help" \
     --type change \
     --description "Tweaks command descriptions for clarity." \
     --author carol \
     --pr 103
   ```
   Each invocation writes a Markdown file inside `unreleased/`. For example,
   `add-pipeline-builder.md` looks like:
   ```markdown
   ---
   title: Add pipeline builder
   type: feature
   authors:
   - alice
   created: 2025-10-16
   prs:
   - 101
   ---

   Introduces the new pipeline builder UI.
   ```

If an entry spans multiple pull requests, repeat `--pr` during `add`. The CLI
stores a `prs:` list in the generated frontmatter automatically, even when
there is only one related pull request.

3. **Preview the changelog:**
   ```sh
   uvx tenzir-changelog show
   ```
   The default table mirrors the old `list` command, summarizing IDs, titles,
   types, projects, pull-request numbers, and authors. Inspect a detailed card
   for any entry with:
   ```sh
   uvx tenzir-changelog show -c 1
   ```

4. **Prepare release notes:**  
   Author an intro snippet that can include Markdown links, call-outs, or image
   references. Save it as `intro.md` (feel free to delete the
   file after publishing the release):
   ```markdown
   Welcome to the first release of the Tenzir changelog!

   ![Release Overview](images/release-overview.png)

     We cover breaking changes, highlights, upgrades, and fixes below.
   ```

5. **Cut the release:**  
   ```sh
   uvx tenzir-changelog release create v0.1.0 \
     --description "Stitches together initial features." \
     --intro-file intro.md
   ```
   Confirm the prompt to include all pending entries. The tool writes the release
   artifacts under `releases/v0.1.0/`:
   - `manifest.yaml` records the release date (and optional intro), while the
     `entries/` subdirectory serves as the authoritative list of shipped files:
     ```yaml
     created: 2025-10-18
     intro: |-
       Welcome to the first release of the Tenzir changelog!

       ![Release Overview](images/release-overview.png)

       We cover breaking changes, highlights, upgrades, and fixes below.
     ```
   - `notes.md` stitches together the description, intro, and generated sections:
     ```markdown
     Stitches together initial features.

     Welcome to the first release of the Tenzir changelog!

     ![Release Overview](images/release-overview.png)

     We cover breaking changes, highlights, upgrades, and fixes below.

     ## Breaking changes

     - **Remove legacy ingest API**: Drops the deprecated endpoints in favor of the stable flow.

     ## Features

     - **Add pipeline builder**: Introduces the new pipeline builder UI.

     ## Bug fixes

     - **Fix ingest crash**: Resolves ingest worker crash when tokens expire.

     ## Changes

     - **Improve CLI help**: Tweaks command descriptions for clarity.
     ```
   - `entries/` contains the archived entry files that were moved out of
     `unreleased/`.

6. **Validate the project:**  
   ```sh
   uvx tenzir-changelog validate
   ```
   A clean run prints `All changelog files look good!`. At this point you have
   entries, an introductory release manifest, and supporting assets ready for
   downstream documentation. You can remove `intro.md` now that its content is
   embedded in the release file.

7. **Export the release:**  
   ```sh
   uvx tenzir-changelog show -m v0.1.0
   ```
   The command prints a Markdown summary grouped by entry type to STDOUT. Use
   `--format json` for machine-readable output or add `-c` for the compact
   bullet list.

## Troubleshooting

- Missing PR metadata often indicates the GitHub CLI is not installed or a
  token is absent. Re-run with `--no-gh` to skip auto-detection when necessary.
- Use `uvx tenzir-changelog validate --strict` pre-commit to block releases with
  inconsistent metadata or unused entries.

## Next Steps

- `uvx tenzir-changelog --help` to explore global flags and advanced filtering
- `uvx tenzir-changelog add --help` for the complete list of metadata prompts
- Configure automation (e.g., GitHub Actions) to run `validate` alongside
  existing documentation or release workflows
