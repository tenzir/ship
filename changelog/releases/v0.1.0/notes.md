This initial version introduces the inaugural `tenzir-changelog` CLI, covering project bootstrapping, entry capture, rich browsing, release assembly, documentation, and validation tooling.

## 🚀 Features

### Assemble release manifests from unreleased entries

Provide a `release` subcommand that collects unreleased entries, writes versioned manifests with archived entry copies, and generates release notes with an optional introduction template.

*By @codex.*

### Bootstrap changelog projects interactively

Ship the `tenzir-changelog bootstrap` command to scaffold a changelog workspace, prompting for project metadata, guessing the default GitHub repository, and preparing config and directories for immediate use.

*By @codex.*

### Browse entries in rich terminal views

Add `list` and `show` commands that render changelog entries in a Rich-powered table, support filtering by project or release, and output Markdown or JSON for downstream tooling.

*By @codex.*

### Capture entries with a guided CLI flow

Introduce the `tenzir-changelog add` workflow that gathers authors, pull requests, and entry types from the terminal, opens an editor for the body, and writes structured Markdown entries without manual file wrangling.

*By @codex.*

## 🔧 Changes

### Publish documentation and agent onboarding guides

Ship README, development, and user guides alongside AI agent context so contributors have a single place to learn the workflows and expectations for `tenzir-changelog`.

*By @codex.*

### Validate changelog projects in CI pipelines

Bundle a `validate` command and GitHub Actions workflow so repositories can enforce formatting, linting, type checks, and changelog integrity on every push.

*By @codex.*
