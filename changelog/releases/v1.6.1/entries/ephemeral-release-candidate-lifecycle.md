---
title: Release candidate cleanup after promotion
type: bugfix
authors:
  - mavam
  - codex
components:
  - cli
  - python
prs:
  - 20
created: 2026-03-20T10:00:06.37057Z
---

This fixes the release candidate workflow so RCs no longer remain in changelog history after they have been superseded. Creating a new `-rc.N` now replaces the previous RC for that cycle, and creating a stable release closes the RC cycle and removes its RC manifests from `releases/`.

For example:

```sh
# Start an RC cycle for a later stable release.
tenzir-ship release create v1.2.3 --rc --yes
tenzir-ship release create v1.3.0 --yes

# Or promote the active RC to its matching stable release.
tenzir-ship release create v1.2.3 --rc --yes
tenzir-ship release create --yes
```

After the stable release is created, the RC is no longer kept in release history. Release candidates are also cumulative, so each new RC includes the previous RC's entries plus any newly added unreleased entries, while stable releases remain incremental.
