# tenzir-ship

`tenzir-ship` is a changelog and release engineering toolkit.

- creating structured changelog entries,
- generating release notes,
- validating changelog structure/content,
- publishing GitHub releases.

## Documentation

<https://docs.tenzir.com/reference/ship-framework.md>

## Repository Layout

- `src/tenzir_ship/`
  - `cli/` — modular CLI implementation
  - `api.py` — `Changelog` Python facade mirroring CLI workflows
  - `config.py` — config loading/dumping (`config.yaml` / `package.yaml` fallback)
  - `entries.py` — entry parsing/writing and metadata normalization
  - `releases.py` — release manifest and release-entry storage helpers
  - `modules.py` — nested changelog project discovery via glob patterns
  - `validate.py` — structure + semantic validation routines
  - `version_files.py` — package-manager version file update helpers
  - `utils.py` — logging, formatting, git/github helpers
- `tests/` — pytest suite (unit + CliRunner integration tests)
- `changelog/` — this repo’s own dogfooded changelog project
- `.github/workflows/` — CI, validation, build, and release workflows

## Dev Commands

- Install dev dependencies:
  - `uv sync --dev`
- Run CLI locally:
  - `uv run tenzir-ship --help`
- Main checks:
  - `uv run ruff check`
  - `uv run ruff format --check`
  - `uv run mypy`
  - `uv run pytest`
- Build package:
  - `uv build`

## Releasing

This repo dogfoods its own reusable release workflow. To cut a release, trigger
the **Release** workflow (`.github/workflows/trigger-release.yaml`) via
`workflow_dispatch` on GitHub Actions. It calls the reusable
`.github/workflows/release.yaml` with project-specific hooks for quality gates,
version bumping, and PyPI publish.

## Skills

The agent skill lives under `skills/tenzir-ship/`.
Keep the skill and its reference files in sync with key user-facing workflows,
especially when changing bootstrap/setup, changelog entry, release, or publish
behavior.
