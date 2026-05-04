This release tightens changelog validation so unknown entry metadata keys are reported before they can be ignored by release workflows.

## 🐞 Bug fixes

### Validation for unknown entry metadata keys

The `validate` command now reports unknown changelog entry metadata keys instead of silently accepting them. This catches misspelled fields such as `co-authors` early, before they are ignored by release workflows.

*By @mavam and @codex in #23.*
