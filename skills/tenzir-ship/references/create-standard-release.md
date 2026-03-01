# Create a release

Cut a release with`tenzir-ship`.

## Pre-release checks

Verify:

1. Git working tree is clean
2. CI is green on the release branch (typically `main`)
3. `uvx tenzir-ship validate` passes

## Gather release metadata

Read unreleased entries to understand all changes for this release. 

### Draft introduction

Read all unreleased entries and identify the single most impactful change that
would make users want to upgrade.

Severity matters more than category: a critical crash may outweigh a minor
feature, but a major new capability may outweigh a rare edge-case fix.


Write a 2–3 sentence introduction that summarizes the theme of the release:

- Sentence 1 states the most impactful change that would make users want to
  upgrade
- Always write in active voice
- Only focus on user-facing impact

### Draft title

Derive the release title from the introduction

Title rules:

- Plain text only
- Sentence case
- Descriptive noun phrase
- No Markdown formatting

## Cut the release

Cut the release by running:

```sh
uvx tenzir-ship release create \
  --title "<title>" \
  --intro "<intro>" \
  --yes
```

This auto-bumps the version to the next version according to the set of
available changelog entries.

For a manual bump, pass to `create` one of `--patch`, `--minor`, or `--major`. 

Only when directly requested, pass an explicit version as position argument for
manual version overrides, e.g., `create v1.2.3`.

Swap `--intro` with `--intro-file` if the introduction contains escape-worthy
characters.
