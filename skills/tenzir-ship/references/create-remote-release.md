# Trigger a remote release

Before triggering the workflow, verify release preconditions locally:

1. Ensure the current branch is `main`.
2. Ensure local `main` and `origin/main` are in sync (no ahead/behind commits).

If either check fails, abort.

## Locate GitHub Actions workflow

Identify the CI release workflow file, e.g., `.github/workflows/release.yaml`.

## Determine release inputs

Inspect the workflow to understand its shape. The release workflow in this
repository accepts these common inputs:

- **intro**: Summarize unreleased entries in `changelog/unreleased/` into 1–2
  sentences describing the release highlights.
- **title**: Identify the lead topic—the single most important change from a
  user's perspective.
- **bump**: Optional manual bump for a stable release (`patch`, `minor`, or
  `major`). Leave this unset or use `auto` unless the user explicitly requests
  a manual bump.
- **version**: Optional explicit version, used for release candidates or when
  the user requests an exact stable version.
- **source-release**: Optional release candidate to promote exactly into the
  matching stable version.
- **current-unreleased**: Optional boolean used when release candidates exist
  but the stable release should be cut from the current unreleased queue
  instead of a candidate snapshot.

If you encounter other inputs, make reasonable choices and inform the user.

## Trigger the workflow

Pick the invocation that matches the requested workflow.

### Stable release with auto-inferred bump

```sh
gh workflow run release.yaml \
  -f intro="<intro text>" \
  -f title="<title>"
```

Do not specify a version bump unless explicitly requested. The workflow will
pick the appropriate bump according to the changelog entry types.

### Stable release with manual bump

```sh
gh workflow run release.yaml \
  -f intro="<intro text>" \
  -f title="<title>" \
  -f bump=<patch|minor|major>
```

### Release candidate

```sh
gh workflow run release.yaml \
  -f intro="<intro text>" \
  -f title="<title>" \
  -f version=v1.2.3-rc.1
```

### Promote a release candidate exactly

```sh
gh workflow run release.yaml \
  -f intro="<intro text>" \
  -f title="<title>" \
  -f version=v1.2.3 \
  -f source-release=v1.2.3-rc.2
```

### Cut the stable release from the current unreleased queue even when RCs exist

```sh
gh workflow run release.yaml \
  -f intro="<intro text>" \
  -f title="<title>" \
  -f version=v1.2.3 \
  -f current-unreleased=true
```

## Monitor the run

Wait briefly for the run to register, find its ID, then watch it.

Verify:

- If the run succeeds, report the GitHub release URL.
- If it fails, report the run URL so the user can inspect the logs.
