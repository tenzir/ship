This release makes promoting release candidates more forgiving. Promoting a candidate to a stable release now works even after you edit entries from the candidate snapshot.

## 🔧 Changes

### Release candidate promotion accepts edited entries

Promoting a release candidate to a stable release no longer fails when an entry from the candidate snapshot was edited in `unreleased/` afterwards. The stable release now uses the edited entry content, just like a follow-up release candidate would.

*By @IyeOnline in #48.*
