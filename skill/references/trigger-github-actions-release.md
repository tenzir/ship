# Create a release via GitHub Actions

Many projects have wrapped the release process into a deterministic GitHub
Actions workflow. A **remote** release delegates the process of releasing to
GitHub Actions CI, without the involvement of any local calls to `tenzir-ship`.

## Locate GitHub Actions workflow

Identify the CI release workflow file, e.g., `.github/workflows/release.yaml`.

## Determine release inputs

Typical release inputs are:

- **intro**: Summarize unreleased entries in `changelog/unreleased/` into 1–2
  sentences describing the release highlights.
- **title**: Identify the lead topic—the single most important change from a
  user's perspective.

If you encounter other inputs, make reasonable choices and inform the user.

## Trigger the workflow

Run the workflow via `gh`:

```sh
gh workflow run release.yaml \
  -f intro="<intro text>" \
  [-f title="<title>"] \
  [-f bump=<patch|minor|major>]
```

The `title` and `bump` fields are optional.

Manual bumping bypasses auto-detection of the next version. Do not specify
it by default.

## Monitor the run

Wait briefly for the run to register, find its ID, then watch it.

## Verify

- If the run succeeds, report the GitHub release URL.
- If it fails, report the run URL so the user can inspect the logs.
