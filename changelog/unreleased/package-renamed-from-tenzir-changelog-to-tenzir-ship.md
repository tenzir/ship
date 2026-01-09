---
title: Package renamed from tenzir-changelog to tenzir-ship
type: breaking
authors:
  - mavam
  - claude
created: 2026-01-09T07:03:27.751861Z
---

The project has been renamed from `tenzir-changelog` to `tenzir-ship`. This includes the package name, CLI command, Python module, and GitHub repository.

**Migration:**

```bash
# Old
uvx tenzir-changelog add

# New
uvx tenzir-ship add
```

```python
# Old
from tenzir_changelog import Changelog

# New
from tenzir_ship import Changelog
```

All command names remain unchanged (`add`, `show`, `validate`, `release`). The repository has moved from `tenzir/changelog` to `tenzir/ship`.

The old `tenzir-changelog` PyPI package will remain available for a transition period but will not receive further updates.
