This release adds support for nested changelog projects through modules, improves export formats with structured URL fields in JSON, and enhances the CLI with better export options and configuration flexibility for components.

## 🚀 Features

### Add `--explicit-links` flag for portable Markdown

**Components:** `cli`

The `show` and `release notes` commands now accept `--explicit-links` to render `@mentions` and `#PR` references as full Markdown links. Use this flag when exporting release notes to documentation sites or other renderers that lack GitHub's auto-linking.

*By @mavam and @claude.*

### Add long option versions for release notes command

**Components:** `cli`

The `release notes` command now accepts long option versions `--markdown` and `--json` in addition to the short `-m` and `-j` flags, improving command discoverability and consistency with other CLI tools.

*By @mavam and @claude.*

### Add modules for nested changelog projects

Modules are nested changelog projects discovered via a configurable glob pattern. Configure `modules` in `config.yaml` with a glob pattern like `../packages/*/changelog` to enable automatic discovery. The `show` command aggregates entries from all modules by default (use `--no-modules` to exclude), and `validate` checks all modules. Use the new `modules` command to list discovered modules with their paths.

*By @mavam and @claude.*

### Add structured URL fields to JSON export format

**Components:** `cli`

The JSON export format now includes structured objects for PRs and authors with explicit URL fields. PRs are exported as `{"number": 123, "url": "..."}` objects (URL included when repository is configured), and authors as `{"handle": "user", "url": "..."}` or `{"name": "Full Name"}` objects. This makes the JSON output self-contained without requiring consumers to construct URLs.

*By @mavam.*

### Support component descriptions in config

The `components` field in `config.yaml` now supports a dict format where keys are component names and values are descriptions:

```yaml
components:
  cli: Command-line interface
  python: Python API and internals
```

The list format remains supported for backward compatibility:

```yaml
components:
  - cli
  - python
```

*By @mavam and @claude.*
