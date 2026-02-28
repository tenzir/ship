# tenzir-ship

`tenzir-ship` is a changelog and release engineering toolkit.

- creating structured changelog entries,
- generating release notes,
- validating changelog structure/content,
- publishing GitHub releases.

## Documentation

https://docs.tenzir.com/reference/ship-framework.md

## Repository Layout

- `src/tenzir_ship/`
  - `cli/` — modular CLI implementation
  - `api.py` — `Changelog` Python facade mirroring CLI workflows
  - `config.py` — config loading/dumping (`config.yaml` / `package.yaml` fallback)
  - `entries.py` — entry parsing/writing and metadata normalization
  - `releases.py` — release manifest and release-entry storage helpers
  - `modules.py` — nested changelog project discovery via glob patterns
  - `validate.py` — structure + semantic validation routines
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
