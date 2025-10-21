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

1. Bootstrap the changelog project inside your repository:
   ```sh
   uvx tenzir-changelog bootstrap
   ```
   The assistant creates the standard directory structure, seeds configuration,
   writes `config.yaml`, and lets you register the project name without touching
   files manually.
2. View the current changelog for your working tree:
   ```sh
   uvx tenzir-changelog
   ```
   The default command renders the local changelog summary using the project
   configuration and any staged or committed entry files.
3. Add a new changelog entry when you prepare a pull request:
   ```sh
   uvx tenzir-changelog add
   ```
   The assistant collects metadata (type, GitHub PR information, authors,
   components) and writes a ready-to-commit Markdown file under `unreleased/`.
   Defaults such as the configured project come from `config.yaml`, so you just
   press enter through most prompts.

## CLI Overview

`tenzir-changelog` offers a focused set of commands. All commands accept
`--config` to point at an explicit configuration file (YAML format, defaulting
to `config.yaml`) and `--root` to operate on another repository.

- **`tenzir-changelog bootstrap`**  
  Initialize or update the changelog project in the current repository. The
  bootstrapper:
  - Creates the `unreleased/` and `releases/` directories
  - Writes a starter `config.yaml` with detected repository details, the project
    name, and GitHub settings
  - Updates the config so future commands can reuse the defaults

- **`tenzir-changelog` / `tenzir-changelog show`**  
  Render the current changelog snapshot. Filters include:
  - `--project <name>` to scope to a single project
  - `--release <id>` to display a specific release manifest
  - `--since <version>` to collate entries newer than the provided version tag

- **`tenzir-changelog add`**
Create a new change entry in `unreleased/`. Highlights:
  - Prompts for change type (`feature`, `bugfix`, `change`) with one-key shortcuts
    (`1`, `2`, `3`), the project, summary, and detailed notes
  - Auto-detects authors, PR number, title, and body via `gh` or the GitHub API
    (requires `GITHUB_TOKEN` when the repository is private)
  - Supports `--web` mode to open a prefilled GitHub file creation URL for
    contributors without local write access
  - Enforces naming conventions, validates required frontmatter, and can append
    changelog fragments to an existing draft entry

- **`tenzir-changelog release create`**
  Assemble a release manifest under `releases/` that lists all unused entry IDs
  for the configured project in `config.yaml`. Release metadata lands in
  `releases/<version>/manifest.yaml`, Markdown notes render in `notes.md`, and
  the command moves every file from `unreleased/` into
  `releases/<version>/entries/` so the release assets travel together. Accepts
  options for release title, version, description, and release date. You can
  supply additional narrative via `--intro-file`, and the CLI prints the
  manifest path plus a summary of included entries.

- **`tenzir-changelog export`**
  Export unreleased changes or a specific release to STDOUT. Use `--release
  <version>` to select a release and `--format markdown|json` (default
  `markdown`) to choose the output format.
  - Tip: Re-run the exporter to refresh an existing release README. For example,
    `uv run tenzir-changelog --root changelog export --release v0.2.0 > changelog/releases/v0.2.0/notes.md`
    rewrites the notes in the standard layout, while adding `--compact` switches
    to the terse summary.

- **`tenzir-changelog validate`**
  Run structural checks across entry files, release manifests, and exported
  documentation. The validator reports missing metadata, unused entries,
  duplicate entry IDs, and configuration drift across repositories.

## Configuration Concepts

- **Project:** Identifies which documentation stream the changelog belongs to.
  Every entry and release references the same project string.
- **Entry:** A changelog consists of a set of entries. Each entry uses one of
  three hard-coded types—`feature`, `bugfix`, or `change`.
- **Configuration File:** Settings live in `config.yaml` by default. The file
  captures repository metadata, the single project name, GitHub repository
  slugs, and any other instance-specific options (such as preferred intro
  templates or asset directories) so commands like `add` and `release create`
  can infer context without repeated flags. All options sit at the top level
  (`id`, `name`, `description`, `repository`, `intro_template`,
  `assets_dir`), making the configuration easy to read and diff. The `id`
  serves as the canonical slug written into entry metadata, while `name`
  provides the human-friendly label surfaced in release titles and CLI output.
- **Repositories:** A project may pull changelog entries from other repositories
  (e.g., satellites or private modules). Configuration entries include the
  repository slug, Git remote URL, and branch-to-track for releases.

## Example Workflows

- **First-time setup:**  
Run `uvx tenzir-changelog bootstrap` in each repository to provision the
  changelog directory layout and project. Repeat with `--update` whenever
  requirements evolve.

- **Daily development:**  
  Developers run `uvx tenzir-changelog add` while preparing pull requests to
  capture changes. CI pipelines can enforce `uvx tenzir-changelog validate` to
  guarantee metadata completeness.

- **Cutting a release:**  
  Maintainers execute `uvx tenzir-changelog release create v5.4.0`, supply the
  introductory notes (or reference a Markdown file with richer content and
  imagery), and review the generated manifest before handing it off to docs.
  The command pulls the project display name from `config.yaml`, so no extra switches
  are required.

## Tutorial

This walkthrough mirrors the dogfooded project under `changelog/` and shows
how to bootstrap a repository, add entries, preview the backlog, and publish a
release manifest with richer introductory material. All commands run from the
project root.

1. **Create a sandbox:**  
   ```sh
   mkdir my-changelog
   cd my-changelog
   uvx tenzir-changelog bootstrap
   ```
   Accept the defaults for project name. When asked for a
   project identifier, enter `changelog`. After the command completes, inspect
   `config.yaml`:
   ```yaml
   id: changelog
   name: changelog
   description: The Tenzir Changelog Management Utility
   repository: tenzir/changelog
   ```

2. **Capture entries:**  
   Record three representative changes with authors and pull-request numbers:
   ```sh
  uvx tenzir-changelog add \
    --title "Add pipeline builder" \
    --type feature \
    --description "Introduces the new pipeline builder UI." \
    --author alice \
    --pr 101

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
   created: '2025-10-16'
   authors:
   - alice
   - bob
   pr: 101
   ---

   Introduces the new pipeline builder UI.
  ```

If an entry spans multiple pull requests, repeat `--pr` during `add` or list them
under a `prs:` key instead of `pr:` when editing YAML manually.

3. **Preview the changelog:**  
   ```sh
   uvx tenzir-changelog show
   ```
   The command renders a table summarizing IDs, titles, types, project,
   pull-request numbers, and authors for unreleased entries.

4. **Prepare release notes:**  
   Author an intro snippet that can include Markdown links, call-outs, or image
   references. Save it as `intro.md` (feel free to delete the
   file after publishing the release):
   ```markdown
   Welcome to the first release of the Tenzir changelog!

   ![Release Overview](images/release-overview.png)

   We cover highlights, upgrades, and fixes below.
   ```

5. **Cut the release:**  
   ```sh
   uvx tenzir-changelog release create v0.1.0 \
     --description "Stitches together initial features." \
     --intro-file intro.md
   ```
   Confirm the prompt to include all pending entries. The tool writes
   `releases/v0.1.0.md`:
   ```markdown
   ---
   version: v0.1.0
   title: Our first release!
   project: changelog
   created: '2025-10-18'
   entries:
   - add-pipeline-builder
   - fix-ingest-crash
   - improve-cli-help
   ---

   Stitches together initial features.

   Welcome to the first release of the Tenzir changelog!

   ![Release Overview](images/release-overview.png)

   We cover highlights, upgrades, and fixes below.
   ```

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
   uvx tenzir-changelog export --release v0.1.0
   ```
   The command prints a Markdown summary grouped by entry type to STDOUT. Use
   `--format json` to generate machine-readable output for automation.

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
