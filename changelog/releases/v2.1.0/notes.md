This patch release ensures changelog authorship metadata represents verified people rather than bots, apps, or tools. The bundled agent skill now validates inferred GitHub identities and keeps tool provenance in commit metadata.

## 🔧 Changes

### Human-only changelog authorship guidance

Changelog author metadata now represents verified people only. The bundled agent skill checks inferred GitHub identities and removes or replaces bot, app, machine-user, and tool attribution; tool provenance belongs in commit metadata instead.

*By @mavam in #44.*
