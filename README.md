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

## 🛠️ Reusable GitHub Actions workflow

This repository ships reusable release workflows under `.github/workflows/`.
External repositories can call them directly.

### Default mode: use the caller repo token

By default, `reusable-release.yaml` and `reusable-release-advanced.yaml` use the
caller repository's built-in `GITHUB_TOKEN`. No Tenzir-specific secrets are
required.

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
```

<details>
<summary>Advanced auth, signing, and release-control options</summary>

### Auth and signing overrides

Both `reusable-release.yaml` and `reusable-release-advanced.yaml` support
optional overrides for:

- `github_app_id` + `github_app_private_key` to mint a GitHub App token
- `push_token` to override the default `GITHUB_TOKEN`
- `git_user_name` and `git_user_email` to customize the git author identity
- `gpg_private_key` to supply the signing key material
- `sign_commits` and `sign_tags` to opt into signing specific Git objects when
  a GPG key is provided

Use `reusable-release-advanced.yaml` when you also need the extra hooks and
release controls it exposes. The simpler `reusable-release.yaml` wrapper keeps
`pre-create`, `post-create`, and `skip-publish` for common release automation
and CI smoke tests, while preserving inherited caller secrets for
secret-backed hook scripts.

```yaml
jobs:
  release:
    uses: tenzir/ship/.github/workflows/reusable-release-advanced.yaml@<pinned-ref>
    permissions:
      contents: write
    with:
      intro: This release improves parser coverage and fixes packaging.
      github_app_id: ${{ vars.MY_GITHUB_APP_ID }}
      git_user_name: release-bot
      git_user_email: release-bot@example.com
      sign_commits: true
      sign_tags: true
    secrets:
      github_app_private_key: ${{ secrets.MY_GITHUB_APP_PRIVATE_KEY }}
      gpg_private_key: ${{ secrets.MY_GPG_PRIVATE_KEY }}
```

Auth precedence is:

1. GitHub App token, when `github_app_id` and `github_app_private_key` are set.
2. `push_token`, when provided.
3. The caller repo's default `GITHUB_TOKEN`.

Use `GITHUB_TOKEN` when the workflow only needs to update the current
repository. Use `push_token` or a GitHub App token when you need pushes or tags
created by the workflow to trigger downstream automation.

### Choose an auth mode

Use the smallest option that fits your release process:

- Use `GITHUB_TOKEN` when you only need to update the current repository.
- Use `push_token` when you want to supply your own token for checkout,
  pushes, or publishing.
- Use `push_token` or a GitHub App token when pushes or tags from the
  workflow must trigger downstream workflows.
- Use `github_app_id` and `github_app_private_key` when you want
  repository-scoped bot automation with a short-lived token.
- Use `gpg_private_key` together with `sign_commits` and/or `sign_tags` when
you want to sign commits or tags. Signing stays disabled by default.
</details>

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
