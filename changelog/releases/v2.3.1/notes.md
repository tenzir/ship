This release keeps changelog entry IDs valid for downstream tooling. Long or accented titles now always produce lowercase kebab-case filenames, and validation rejects unreleased entries whose filenames break that rule.

## 🐞 Bug fixes

### Long entry titles no longer produce filenames ending in a dash

A title longer than 80 characters could produce an entry ID ending in a dash when the cut fell right after a word. The `add` command now strips that dash, and `validate` rejects unreleased entry filenames that are not lowercase kebab-case, so such a name fails before it reaches downstream tooling.

Generated IDs are now ASCII-only as well: accented letters lose their accents, so a title like "Café support" produces `cafe-support.md`. A title without any ASCII letters or digits now fails with an error instead of creating `project.md`.

If you named unreleased entries by hand, rename any file that is not lowercase kebab-case, such as `Fix-Login.md`, before you upgrade: `validate` and `release create` now reject them.

*By @zedoraps in #51.*
