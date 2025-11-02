This release adds support for multi-project operations and package-aware discovery.

## 🚀 Features

### Adopt package-aware project discovery

The new *package* concept allows for an alternate way of configuring a changelog project. [Tenzir Packages](https://docs.tenzir.com/explanations/packages/) have a top-level `package.yaml` file that contains the package configuration. When a changelog directory exists within a package directory, it is now possible to omit the `changelog/config.yaml` configuration file. Instead, the changelog CLI will take `id` and `name` from the `package.yaml` file.

This commit also has a few other drive-by improvements:

- On first use, the CLI now scaffolds the `changelog/` workspace implicitly, so `tenzir-changelog add` works from any directory even before the changelog tree exists.
- Interactive prompts now exit cleanly with an explicit error message when cancelled with Ctrl+C, avoiding confusing stack traces.
- New projects no longer sprout an empty `releases/` directory; we only create it once release manifests are generated.

*By @codex and @mavam.*

### Support multi-project changelog operations

Adds support for managing changelogs across multiple projects with a single command. You can now use multiple `--root` flags to operate on multiple changelog projects simultaneously.

The `show` command displays entries from all projects in a unified table with a Project column, making it easy to see unreleased changes across your entire product ecosystem.

The `show` command with markdown or JSON export (`-m` or `-j`) groups entries by project, following a hierarchical format: version → project → entry type → entries.

Table filtering works equally well across multiple projects: `--project` and `--component` constraints are honored, duplicate entry identifiers stay mapped to their original project, and `tenzir-changelog show <version>` returns the coordinated release rows across all roots.

The `release create` command with multiple roots performs coordinated release creation, atomically creating the same version across all projects and moving unreleased entries to releases in each project. Run it without `--yes` for a dry run that previews the release entry counts before you ship.

This feature enables teams with multi-repo or monorepo architectures to maintain coordinated releases with unified changelog documentation.
