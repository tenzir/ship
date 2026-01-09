# 🚀 tenzir-ship

`tenzir-ship` is a release engineering accelerator for software teams. It
streamlines the path from code to production by automating changelog
management, release coordination, and shipping workflows across repositories.

## ✨ Highlights

- 📝 **Changelog management**: Capture entries via an interactive assistant that
  pulls metadata from Git and GitHub, pre-filling authors and PR references.
- 📦 **Release assembly**: Create release manifests with narrative introductions
  and structured entry lists, ready for documentation pipelines.
- ✅ **Validation**: Ensure entry metadata and release manifests stay consistent
  and complete across your project.
- 🔧 **Extensible**: YAML configuration and a Python API for integration into
  custom release workflows.

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
