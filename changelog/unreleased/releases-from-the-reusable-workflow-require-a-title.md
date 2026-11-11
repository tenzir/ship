---
title: Releases from the reusable workflow require a title
type: change
authors:
  - zedoraps
prs:
  - 50
created: 2026-11-11T07:38:17.329726Z
---

The reusable release workflow now fails early when the `title` input is empty or missing. Before, it created a release manifest without a title, which changelog consumers such as the one on tenzir.com reject. If you call the workflow, pass a short headline for the release's main theme as `title`.
