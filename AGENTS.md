# Repository Guidelines

## Project Structure & Module Organization

- `src/tenzir_changelog/` hosts the CLI; `cli.py` registers Click commands and
  companion modules (`config.py`, `entries.py`, `releases.py`, `validate.py`,
  `utils.py`) cover config, entries, releases, validation, and shared helpers.
  Keep changes typed and centralize helpers in `utils.py`.
- `changelog/` stores this repository's changelog project; run CLI commands
  with `--root changelog` so they operate on the dogfooded data and refresh
  those files alongside root docs (`README.md`, `DOCUMENTATION.md`,
  `DEVELOPMENT.md`) when behavior changes.
- `tests/` stores pytest suites that exercise flows with `CliRunner`; mirror
  module names (e.g., `test_cli.py`) and keep fixtures close to usage.

## Compatibility Strategy

- Backwards compatibility is not a priority right now. Prefer simplifying the
  codebase and documentation, even if that means breaking existing behavior or
  data layouts.
- Update the dogfooded project in `changelog/` alongside the CLI whenever
  formats change instead of layering shims.

## Build, Test, and Development Commands

- `uv sync --python 3.12` provisions dependencies into `.venv/`.
- `uv run ruff format` (or `--check`) enforces formatting; follow with `uv run
  ruff check` for linting (E, F).
- `uv run pytest` runs the suite; add `--cov=src/tenzir_changelog` when updating
  coverage.
- `uv run mypy` keeps strict typing; fix warnings rather than ignoring them.
- `uv run check-release` chains formatter, lint, typing, tests, and build—run
  before every PR.
- `uv build` emits sdist and wheel artifacts for smoke tests or releases.

## Coding Style & Naming Conventions

- `ruff` controls whitespace: spaces for indents, double quotes, and a
  80-character limit; let it order imports.
- Type hints are required (`mypy` strict); annotate public APIs and avoid `Any`.
- Use `snake_case` for modules, functions, and variables; reserve `PascalCase`
  for classes and `CONSTANT_CASE` for constants.
- Prefer kebab-case for CLI flags and keep user messages concise.

## Testing Guidelines

- pytest discovers `test_*.py` and `*_test.py`; model coverage on
  `tests/test_cli.py` with `CliRunner` end-to-end flows.
- Maintain ≥80% coverage (enforced by coverage config). Run `uv run pytest
  --cov=src/tenzir_changelog --cov-report=term-missing` before review.
- Move shared fixtures to `tests/conftest.py` when needed and favour `tmp_path`
  for project tests.

## Writing Changelog Entries

- When you implement new changes, features, or fix bugs, create a new changelog
  entry with `uv run tenzir-changelog --root changelog add ...`; do not
  hand-write changelog entry files.
- If you are a coding agent, use your own name as author, e.g., claude or codex.
- Focus on the user-facing impact of your changes. Do not mention internal
  implementation details.
- Always begin with one sentence or paragraph that concisely describes the
  change.
- If helpful, add examples of how to use a the new feature or how to fix the
  bug. A changelog entry can have multiple paragraphs and should read like a
  concise micro-blog post that spotlights the change.
- Make deliberate use of Markdown syntax, e.g., frame technical pieces of the
  code base in backticks, e.g., `--option 42` or `cmd`. Use emphasis and bold
  where it feels appropriate and improves clarity.

## Commit & Pull Request Guidelines

- Write commits in the imperative with a single focus, e.g., `Support manifest
  previews`; explain motivation in the body if needed.
- Before committing anything, always run `uv run check-release`. Fix any
  failures before issuing the actual commit.
- Every PR should mention the changes from a user perspective. Copy the
  user-facing changes from the changelog entry.
