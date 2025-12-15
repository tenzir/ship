---
title: Add structured URL fields to JSON export format
type: feature
author: mavam
components: [cli]
created: 2025-12-15T08:39:53.673596Z
---

The JSON export format now includes structured objects for PRs and authors with explicit URL fields. PRs are exported as `{"number": 123, "url": "..."}` objects (URL included when repository is configured), and authors as `{"handle": "user", "url": "..."}` or `{"name": "Full Name"}` objects. This makes the JSON output self-contained without requiring consumers to construct URLs.
