This initial version introduces the inaugural `tenzir-changelog` CLI, covering project bootstrapping, entry capture, rich browsing, release assembly, documentation, and validation tooling.

## 🚀 Features

- Provide a `release` subcommand that collects unreleased entries, writes versioned manifests with archived entry copies, and generates release notes with an optional introduction template. (by @codex)
- Ship the `tenzir-changelog bootstrap` command to scaffold a changelog workspace, prompting for project metadata, guessing the default GitHub repository, and preparing config and directories for immediate use. (by @codex)
- Add `list` and `show` commands that render changelog entries in a Rich-powered table, support filtering by project or release, and output Markdown or JSON for downstream tooling. (by @codex)
- Introduce the `tenzir-changelog add` workflow that gathers authors, pull requests, and entry types from the terminal, opens an editor for the body, and writes structured Markdown entries without manual file wrangling. (by @codex)

## 🔧 Changes

- Ship README, development, and user guides alongside AI agent context so contributors have a single place to learn the workflows and expectations for `tenzir-changelog`. (by @codex)
- Bundle a `validate` command and GitHub Actions workflow so repositories can enforce formatting, linting, type checks, and changelog integrity on every push. (by @codex)
