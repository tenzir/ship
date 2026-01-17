---
title: Progress tracking for release publish failures
type: feature
authors:
  - mavam
  - claude
created: 2026-01-17T10:17:46.607669Z
---

The `release publish` command now displays a progress summary when a step fails mid-workflow, showing which steps completed successfully and which step failed.

When using `--commit` or `--tag` flags, the publish workflow executes multiple git operations (commit, tag, push branch, push tag) before publishing to GitHub. If any step fails, you now see a panel with checkmarks for completed steps, an X for the failed step, and circles for pending steps. This helps you understand exactly where the workflow stopped and what manual commands you need to run to recover.

For example, if the branch push fails due to network issues, you'll see that the commit and tag were created successfully, the push failed, and the tag push and GitHub publish are still pending—making it clear you can safely retry after fixing the network issue.
