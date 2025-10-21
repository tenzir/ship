# 📝 tenzir-changelog

`tenzir-changelog` is the reusable changelog companion for Tenzir projects. It
helps contributors capture entries, maintain release manifests, and ship tidy
change logs across public and private repositories.

## ✨ Highlights

- 🚀 Bootstrap a changelog project with sensible defaults and YAML
  configuration in seconds.
- 🧾 Capture changelog entries via an interactive assistant that pulls metadata
  from Git and GitHub.
- 📦 Assemble release manifests that include narrative introductions before the
  structured list of entries.
- 🔍 Validate entry metadata and release manifests to keep docs tooling happy.

## 📦 Installation

`tenzir-changelog` ships on PyPI. Use
[`uvx`](https://docs.astral.sh/uv/concepts/tools/) to fetch and execute the
latest compatible version on demand (requires Python 3.12+):

```sh
uvx tenzir-changelog --help
```

`uvx` downloads the newest release, runs it in an isolated environment, and
caches the result for snappy subsequent invocations.

## 📚 Documentation

- [User guide](DOCUMENTATION.md) — CLI walkthroughs, configuration concepts, and
  a hands-on tutorial.
- [Development guide](DEVELOPMENT.md) — local workflows, quality gates, and
  release procedures for maintainers.

## 🧪 Dogfooded Project

The repository ships with `changelog/`, the real changelog project maintained
by the Tenzir team. Explore it to see how `config.yaml`, `unreleased/`, and
Markdown release manifests fit together end-to-end.

## 📄 License

`tenzir-changelog` is released under the Apache License, Version 2.0. Consult
[`LICENSE`](LICENSE) for the full text.
