# tenzir-ship

`tenzir-ship` is a changelog and release engineering toolkit.

Use cases:

- Creating structured changelog entries
- Generating release notes
- Validating changelog structure/content
- Publishing GitHub releases

## Documentation

Documentation for `tenzir-ship` lives in the `tenzir/content` GitHub repository
under `website/src/content/docs/`. When making user-facing changes, update the
docs by creating a local clone in `.docs/` and file a companion PR alongside the
main code PR.

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

## Entry IDs

An entry's ID is its filename stem: `add` derives it once from the title, and
every other command reads it back from the filename. The `tenzir/news` sync,
which feeds the changelog on tenzir.com, rejects any unreleased entry whose stem
is not lowercase kebab-case (`[a-z0-9]+(-[a-z0-9]+)*`). Both
`generate_entry_id` and the `validate` structure check enforce
`ENTRY_ID_PATTERN` from `entries.py`; change the rule only there.

## Dev Commands

- Install dev dependencies:
  - `uv sync --dev`
- Run CLI locally:
  - `uv run tenzir-ship --help`
- Full validation:
  - `uv run ruff check`
  - `uv run ruff format --check`
  - `uv run mypy`
  - `uv run pytest --durations=10`
  - `uv run tenzir-ship --root changelog validate`
- Build package:
  - `uv build`

## Releasing

This repo dogfoods its own reusable release workflow.

To cut a release, trigger the **Release** workflow
(`.github/workflows/trigger-release.yaml`). It calls the reusable
`.github/workflows/release.yaml` with project-specific hooks for quality gates,
version bumping, and PyPI publish.

## Agent skill

The `tenzir-ship` agent skill lives under `skills/tenzir-ship/`.

Keep the skill and its reference files in sync with documentation.
