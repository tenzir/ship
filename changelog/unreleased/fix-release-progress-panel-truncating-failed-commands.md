---
title: Fix release progress panel truncating failed commands
type: bugfix
authors:
  - mavam
  - claude
pr: 7
created: 2026-02-15T10:29:09.765161Z
---

When a release step fails, the full command now prints below the progress panel so you can copy-paste it for manual recovery.

Previously, long commands would get truncated in the release progress panel, making it difficult to reproduce the failure manually. Now when a step fails, the complete command is displayed in full below the panel, giving you what you need to debug and retry the operation.
