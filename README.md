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

This repository ships a reusable release workflow at
`.github/workflows/release.yaml`. External repositories can call it directly.
Pin the workflow to a released tag or full commit SHA instead of a moving
branch name.

```yaml
jobs:
  release:
    uses: tenzir/ship/.github/workflows/release.yaml@<pinned-ref>
    permissions:
      contents: write
    with:
      intro: This release improves parser coverage and fixes packaging.
      bump: auto
```

The workflow supports GitHub App tokens, static push tokens, GPG signing,
pre/post hooks, and several release-control options. See the
[reference](https://docs.tenzir.com/reference/ship-framework) for the full list
of inputs, secrets, and auth modes.

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
