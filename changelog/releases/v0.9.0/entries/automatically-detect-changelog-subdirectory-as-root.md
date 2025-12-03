---
title: Automatically detect changelog/ subdirectory as root
type: feature
author:
- claude
- mavam
pr: 4
component: cli
created: 2025-12-03T19:58:29.7171Z
---

The CLI now automatically uses a `changelog/` subdirectory as the project root when running commands from the parent directory. This means you no longer need to pass `--root changelog` when the current directory contains a valid changelog project in a `changelog/` subdirectory.
