This release improves how changelog projects handle PR metadata. The new require_pr option lets validation remind you when an unreleased entry still lacks its pull request reference, and projects that set omit_pr or omit_author now get validation support to keep stray metadata from slipping in.

## 🚀 Features

### Required PR metadata validation

Projects can now set `require_pr: true` in their changelog configuration to make plain validation fail when an unreleased entry is missing `prs` metadata:

```sh
tenzir-ship validate
```

Use `tenzir-ship validate --lenient` in pre-push hooks to keep missing PR numbers as warnings until the pull request exists. Other validation errors still fail in lenient mode.

*By @zedoraps and @codex in #34.*

## 🔧 Changes

### Agent skill respects PR and author omission options

The `tenzir-ship` agent skill no longer instructs agents to record PR numbers or authors in projects whose config sets `omit_pr: true` or `omit_author: true`, and now runs `tenzir-ship validate` after creating or editing an entry. Previously, the skill's guidance to manually write PR numbers into entry frontmatter bypassed these options.

*By @zedoraps in #33.*

### Validation rejects PR and author metadata when omitted by config

The `validate` command now reports an error when an entry carries `prs` metadata while the config sets `omit_pr: true`, or `authors` metadata while the config sets `omit_author: true`. Previously, entries written directly to disk could bypass these options, which only guarded the `add` command.

*By @zedoraps in #32.*
