---
title: Support component descriptions in config
type: feature
authors:
  - mavam
  - claude
created: 2025-12-15T09:24:03.346651Z
---

The `components` field in `config.yaml` now supports a dict format where keys are component names and values are descriptions:

```yaml
components:
  cli: Command-line interface
  python: Python API and internals
```

The list format remains supported for backward compatibility:

```yaml
components:
  - cli
  - python
```
