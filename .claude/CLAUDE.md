# Repository Structure

## CLI

`src/tenzir_changelog/` contains the Click-based CLI:

- `cli.py`: command registration and entry points
- `config.py`: project configuration handling
- `entries.py`: changelog entry management
- `releases.py`: release manifest operations
- `validate.py`: entry and manifest validation
- `utils.py`: shared helpers
- `api.py`: programmatic API

## Tests

`tests/` contains pytest suites using `CliRunner` for end-to-end CLI testing.

## Dogfooded Project

`changelog/` is this repository's own changelog project:

- `config.yaml`: project configuration
- `unreleased/`: pending changelog entries
- `releases/`: version directories with release manifests
