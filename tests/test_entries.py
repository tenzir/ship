"""Tests for entry helper utilities."""

from __future__ import annotations

from pathlib import Path

from tenzir_changelog.entries import iter_entries, sort_entries_desc, write_entry


def test_sort_entries_desc_orders_by_numeric_prefix(tmp_path: Path) -> None:
    metadata_a = {"title": "Entry A", "type": "change", "component": "cli"}
    metadata_b = {"title": "Entry B", "type": "change", "component": "cli"}

    entry_a = write_entry(tmp_path, dict(metadata_a), "First body")
    entry_b = write_entry(tmp_path, dict(metadata_b), "Second body")

    entries = list(iter_entries(tmp_path))
    ordered = sort_entries_desc(entries)

    assert [entry.entry_id for entry in ordered] == [entry_b.stem, entry_a.stem]
    assert ordered[0].sequence == 2
    assert ordered[1].sequence == 1
