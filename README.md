# 🚀 tenzir-ship

`tenzir-ship` helps you ship faster with automated release engineering. Manage
changelogs, generate release notes, and publish GitHub releases.

## ✨ Highlights

- 📝 **Changelog management**: Capture entries via an interactive assistant that
  pulls metadata from Git and GitHub, pre-filling authors and PR references.
- 📦 **Release notes**: Generate release notes from structured entries, ready
  for documentation pipelines or direct publishing.
- 🚀 **GitHub releases**: Publish releases directly to GitHub with generated
  notes and assets.
- 🔖 **Opinionated versioning**: Release manifests and package files use bare
  semantic versions such as `1.2.3`, while Git and GitHub releases are tagged
  as `v1.2.3`.
- 🔧 **CLI and Python API**: Use the command line for interactive workflows or
  the Python API for automation.

## 📦 Installation

`tenzir-ship` ships on PyPI. Use
[`uvx`](https://docs.astral.sh/uv/concepts/tools/) to fetch and execute the
latest compatible version on demand (requires Python 3.12+):

```sh
uvx tenzir-ship --help
```

`uvx` downloads the newest release, runs it in an isolated environment, and
caches the result for snappy subsequent invocations.

## 🤖 Agent Skill

Install the skill via Vercel Skills:

```sh
npx skills add tenzir/ship
```

## 🛠️ Reusable GitHub Actions Workflow

This repository ships a reusable release workflow at
`.github/workflows/reusable-release.yaml`. External repositories can call it
directly.

By default, `reusable-release.yaml` uses the caller repository's built-in
`GITHUB_TOKEN`. No Tenzir-specific secrets are required.

Use this mode when you want a self-contained release workflow in the caller
repository. If your release process must trigger downstream workflows from the
resulting pushes or tags, use `push_token` or a GitHub App token instead.

Pin the workflow to a released tag or full commit SHA instead of a moving branch
name. Replace `<pinned-ref>` below with the immutable ref you want to consume.

```yaml
jobs:
  release:
    uses: tenzir/ship/.github/workflows/reusable-release.yaml@<pinned-ref>
    permissions:
      contents: write
    with:
      intro: This release improves parser coverage and fixes packaging.
      bump: auto
      workflow_source_repository: tenzir/ship
      workflow_source_ref: <pinned-ref>
```

### Auth and signing overrides

`reusable-release.yaml` supports these optional auth and signing overrides:

- `github_app_id` + `github_app_private_key` to mint a GitHub App token.
- `use_push_token` + `push_token` to opt into a custom token instead of the
  default `GITHUB_TOKEN`.
- `workflow_source_token` to authenticate the checkout of the workflow source
  repository when the reusable workflow lives in a different private or
  internal repository than the caller.
- `git_user_name` and `git_user_email` to customize the git author identity.
- `gpg_private_key` to enable GPG signing.
- `sign_commits` and `sign_tags` (both default to `false`) to control which Git
  objects are signed when a GPG key is provided. You must set at least one to
  `true` for signing to take effect.

### Hooks and release controls

The same workflow also exposes the advanced hooks and release controls:
`pre-create`, `post-create`, `pre-publish`, `post-publish`, `skip-publish`,
`publish-no-latest-on-non-main`, `copy-release-to-main-on-non-main`, and
`update-latest-branch-on-main`.

Callers must also set `workflow_source_repository` and `workflow_source_ref` so
the workflow can checkout and install the same `tenzir-ship` source that
defines the reusable workflow. For external callers, set these to the same
repository/ref pair you use in `uses:`. For same-repository callers, pass
`${{ github.repository }}` and `${{ github.sha }}`.

Pass hook scripts via `with:`. If your hook scripts need secrets, same-org or
same-enterprise callers can keep using `secrets: inherit`. External callers
that cannot inherit secrets can pass a `hook_env` secret containing
newline-delimited `KEY=value` assignments. The workflow **sources** this value
as a shell script (`set -a; . <(...); set +a`) before each hook runs, so
standard shell quoting rules apply. For example:

```text
REGISTRY_URL=https://registry.example.com
DEPLOY_TOKEN=ghp_abc123
NPM_CONFIG_REGISTRY="https://npm.example.com/"
```

> [!CAUTION]
> Because `hook_env` is sourced as shell, values with unquoted metacharacters
> like `;`, `$`, or backticks are interpreted. Quote values that contain special
> characters and avoid embedding secrets that should not appear in runner logs —
> GitHub masks the entire `hook_env` blob but not individual values extracted
> from it.

```yaml
jobs:
  release:
    uses: tenzir/ship/.github/workflows/reusable-release.yaml@<pinned-ref>
    permissions:
      contents: write
    with:
      intro: This release improves parser coverage and fixes packaging.
      workflow_source_repository: tenzir/ship
      workflow_source_ref: <pinned-ref>
      pre-publish: ./scripts/prepare-release.sh
      post-publish: ./scripts/announce-release.sh
      update-latest-branch-on-main: true
      github_app_id: ${{ vars.MY_GITHUB_APP_ID }}
      git_user_name: release-bot
      git_user_email: release-bot@example.com
      sign_commits: true
      sign_tags: true
    secrets:
      github_app_private_key: ${{ secrets.MY_GITHUB_APP_PRIVATE_KEY }}
      gpg_private_key: ${{ secrets.MY_GPG_PRIVATE_KEY }}
```

If you prefer an explicit push token, opt into it with `use_push_token: true`
and pass the token as a secret:

```yaml
jobs:
  release:
    uses: tenzir/ship/.github/workflows/reusable-release.yaml@<pinned-ref>
    permissions:
      contents: write
    with:
      intro: This release improves parser coverage and fixes packaging.
      workflow_source_repository: tenzir/ship
      workflow_source_ref: <pinned-ref>
      use_push_token: true
    secrets:
      push_token: ${{ secrets.MY_PUSH_TOKEN }}
```

If the reusable workflow itself is hosted in a different private or internal
repository, pass a separate checkout token for that repository as well:

```yaml
jobs:
  release:
    uses: tenzir/ship/.github/workflows/reusable-release.yaml@<pinned-ref>
    permissions:
      contents: write
    with:
      intro: This release improves parser coverage and fixes packaging.
      workflow_source_repository: tenzir/ship
      workflow_source_ref: <pinned-ref>
    secrets:
      workflow_source_token: ${{ secrets.MY_WORKFLOW_SOURCE_TOKEN }}
```

Auth precedence is:

1. GitHub App token, when `github_app_id` and `github_app_private_key` are set.
2. `push_token`, when `use_push_token: true` and the secret is set.
3. The caller repo's default `GITHUB_TOKEN`.

### Migration

`reusable-release-advanced.yaml` has been removed. Callers that previously used
that path should switch to `reusable-release.yaml`; the advanced hooks and
release controls now live on the same file.

### Choose an auth mode

Pick the smallest option that fits your release process:

- Keep the default `GITHUB_TOKEN` when you only need to update the current
  repository.
- Set `use_push_token: true` and pass `push_token` when you want to supply your
  own token for checkout, pushes, or publishing, or when pushes or tags from
  the workflow must trigger downstream workflows.
- Pass `workflow_source_token` when the reusable workflow comes from a
  different private or internal repository and your primary auth token only
  needs access to the caller repository.
- Set `github_app_id` and `github_app_private_key` when you want
  repository-scoped bot automation with a short-lived token.
- Provide `gpg_private_key` and set `sign_commits: true` and/or
  `sign_tags: true` when you want to sign commits or tags. Signing stays
  disabled unless you both provide a key and explicitly enable it.

## 📚 Documentation

Consult our [user
guide](https://docs.tenzir.com/guides/packages/maintain-a-changelog)
for an end-to-end walkthrough of maintaining changelogs.

We also provide a dense
[reference](https://docs.tenzir.com/reference/ship-framework) that explains
concepts, abstractions, and CLI details.

## 🐶 Dogfooded Project

The repository ships with [`changelog/`](changelog/), the real changelog project
maintained by the Tenzir team. Explore it to see how
[`config.yaml`](changelog/config.yaml), `unreleased/`, and Markdown release
manifests fit together end-to-end.

## 🤝 Contributing

Want to contribute? We're all-in on agentic coding with [Claude
Code](https://claude.ai/code)! The repo comes pre-configured with our [custom
plugins](https://github.com/tenzir/claude-plugins)—just clone and start hacking.

## 📄 License

`tenzir-ship` is released under the Apache License, Version 2.0. Consult
[`LICENSE`](LICENSE) for the full text.
