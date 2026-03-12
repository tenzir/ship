Release commands now handle mixed version formats consistently, making changelog automation more robust. The bundled GitHub Actions workflows are updated to Node 24-compatible action versions, keeping CI aligned with GitHub's runtime transition.

## 🔧 Changes

### Node 24-ready GitHub Actions workflows

The bundled GitHub Actions workflows now use Node 24-compatible action versions, which keeps CI, release, and publishing automation aligned with GitHub's runtime transition. The release and sync workflows also mint GitHub App installation tokens without relying on a deprecated JavaScript action.

*By @mavam and @pi.*

## 🐞 Bug fixes

### More robust release version normalization

Release commands and the Python API now handle release versions more consistently when changelog data mixes tag-style versions such as `v1.2.3` with bare semantic versions such as `1.2.3`. This improves compatibility with existing changelog histories and makes release automation more reliable across commands that inspect, create, show, and publish releases.

*By @mavam and @pi.*
