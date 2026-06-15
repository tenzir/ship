This release keeps the unreleased changelog directory anchored after creating releases. It prevents changelog entries from long-lived branches from moving into already cut release notes during rebases or merges.

## 🐞 Bug fixes

### Stable unreleased changelog directory after releases

`release create` now keeps `unreleased/` anchored after consuming entries so Git no longer moves changelog entries from long-lived branches into the just-created release during rebases or merges.

This prevents entries for unreleased work from accidentally appearing in release notes that were already cut.

*By @codex in #29.*
