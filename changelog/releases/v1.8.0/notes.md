This release makes stable promotion from a release candidate include changelog entries added after the last candidate, so the final manifest and notes no longer miss late fixes. It also improves changelog automation guidance and gives the validation status check a clearer name.

## 🔧 Changes

### Changelog entry history guidance

The bundled agent skill now tells release automation to preserve published changelog history while still allowing clearly related unreleased entries to be merged before release.

Historical release notes, manifests, and released entry files are treated as immutable records, with edits reserved for explicit severe publication fixes. For unreleased work, agents now check whether a related entry already exists and merge it instead of creating duplicate changelog entries, reconciling the title, type, and description while appending distinct authors, pull request numbers, and components.

The merge guidance now requires a clear relationship based on the user-facing outcome, not just nearby implementation work, shared files, authors, or PR timing. Ambiguous changes should get a separate entry, and unrelated unreleased entries must remain untouched.

*By @mavam and @codex.*

### Readable changelog validation check name

The changelog validation workflow now appears as `Validate changelog` in GitHub status checks instead of the raw job id `validate`, making required branch checks easier to identify.

*By @mavam and @codex in #27.*

## 🐞 Bug fixes

### RC promotion includes entries added after the last candidate

Promoting a release candidate to a stable release now folds in changelog entries added to `unreleased/` after the last candidate snapshot. The folded entries appear in the release manifest and notes, and are consumed from the unreleased queue. Previously they were silently left behind and missing from the stable release notes. The confirmation table now marks entries carried over from the candidate with a dim bullet and newly folded entries with a plus sign.

*By @mavam in #28.*
