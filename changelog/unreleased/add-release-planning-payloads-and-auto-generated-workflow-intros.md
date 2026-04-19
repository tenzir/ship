---
title: Add release planning payloads and auto-generated workflow intros
type: feature
author: codex
created: 2026-04-03T19:11:53.234426Z
---

tenzir-ship now exposes `release plan --json` for structured release automation, and the bundled release trigger workflow can derive its intro automatically from that plan when the workflow dispatch leaves the intro empty.
