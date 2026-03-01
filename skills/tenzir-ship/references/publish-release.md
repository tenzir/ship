# Publish a release

Publishing a release to GitHub performs the following steps:

1. Commit the release artifacts
2. Create a (signed) git tag
3. Push to git remote
4. Create a release via the GitHub API

## Procedure

Ensure that you have succesfully [created a release](create-standard-release.md).

Thereafter, run:

```sh
uvx tenzir-ship release publish \
  --commit \
  --tag \
  --yes
```

Notes:

- The `--commit` flag commits the changes of the release creation
- The `--tag` option creates an annotated tag (that gets pushed automatically)
- Add `--draft` if the user requested a draft release
- Add `--prerelease` if the user requested marking the release as prerelease
- Add `--no-latest` if the user requested that the release must not be marked as latest
