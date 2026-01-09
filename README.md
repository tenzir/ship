# 📝 tenzir-ship

`tenzir-ship` is the reusable changelog companion for Tenzir projects. It
helps contributors capture entries, maintain release manifests, and ship tidy
change logs across public and private repositories.

## ✨ Highlights

- 🚀 Bootstrap a changelog project with sensible defaults and YAML
  configuration in seconds.
- 🧾 Capture changelog entries via an interactive assistant that pulls metadata
  from Git and GitHub, pre-filling authors from your `gh` login and current PRs.
- 📦 Assemble release manifests that include narrative introductions before the
  structured list of entries.
- 🔍 Validate entry metadata and release manifests to keep docs tooling happy.

## 📦 Installation

`tenzir-ship` ships on PyPI. Use
[`uvx`](https://docs.astral.sh/uv/concepts/tools/) to fetch and execute the
latest compatible version on demand (requires Python 3.12+):

```sh
uvx tenzir-ship --help
```

`uvx` downloads the newest release, runs it in an isolated environment, and
caches the result for snappy subsequent invocations.

## 📚 Documentation

Consult our [user
guide](https://docs.tenzir.com/guides/package-management/maintain-a-changelog)
for an end-to-end walkthrough of maintaining changelogs.

We also provide a dense
[reference](https://docs.tenzir.com/reference/changelog-framework) that explains
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
