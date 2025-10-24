---
title: Refine release workflow
type: change
authors:
- codex
created: 2025-10-24
---

Split the release command into dedicated `release create`, `release notes`, and `release publish` subcommands. Release creation now insists on `--yes` before mutating state, appends unreleased entries to an existing tag, keeps the manifest lean, remembers the chosen layout, and surfaces a dry-run summary. New `--patch`, `--minor`, and `--major` flags bump from the latest tagged release (respecting prefixes), while `release notes` re-exports any release (including `-`) and `release publish` pushes to GitHub via `gh`.
