"""Tests for entry helper utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from tenzir_ship.entries import iter_entries, read_entry, sort_entries_desc, write_entry


def test_sort_entries_desc_orders_by_created_datetime(tmp_path: Path) -> None:
    """Entries are sorted from newest to oldest by created datetime."""
    metadata_a = {
        "title": "Entry A",
        "type": "change",
        "components": ["cli"],
        "created": datetime(2024, 1, 1, 10, 0, 0),
    }
    metadata_b = {
        "title": "Entry B",
        "type": "change",
        "components": ["cli"],
        "created": datetime(2024, 2, 1, 11, 0, 0),
    }

    write_entry(tmp_path, dict(metadata_a), "First body")
    write_entry(tmp_path, dict(metadata_b), "Second body")

    entries = list(iter_entries(tmp_path))
    ordered = sort_entries_desc(entries)

    assert [entry.entry_id for entry in ordered] == ["entry-b", "entry-a"]
    assert ordered[0].created_at == datetime(2024, 2, 1, 11, 0, 0, tzinfo=timezone.utc)
    assert ordered[1].created_at == datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def test_read_entry_normalizes_list_metadata(tmp_path: Path) -> None:
    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\nauthors: mavam\nprs: 42\ncomponents: cli\n---\nBody text.\n",
        encoding="utf-8",
    )

    entry = read_entry(entry_file)

    assert entry.metadata["authors"] == ["mavam"]
    assert entry.metadata["prs"] == [42]
    assert entry.metadata["components"] == ["cli"]
    assert entry.components == ["cli"]


def test_read_entry_normalizes_singular_legacy_metadata(tmp_path: Path) -> None:
    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\nauthor: codex\npr: 42\ncomponent: cli\n---\nBody text.\n",
        encoding="utf-8",
    )

    entry = read_entry(entry_file)

    assert "author" not in entry.metadata
    assert "pr" not in entry.metadata
    assert "component" not in entry.metadata
    assert entry.metadata["authors"] == ["codex"]
    assert entry.metadata["prs"] == [42]
    assert entry.metadata["components"] == ["cli"]
    assert entry.component == "cli"


def test_read_entry_rejects_mixed_singular_and_plural_metadata(tmp_path: Path) -> None:
    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\nauthor: codex\nauthors:\n  - mavam\n---\nBody text.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="both 'author' and 'authors'"):
        read_entry(entry_file)


def test_write_entry_normalizes_singular_legacy_metadata(tmp_path: Path) -> None:
    path = write_entry(
        tmp_path,
        {
            "title": "Test Entry",
            "type": "feature",
            "author": "codex",
            "pr": 42,
            "component": "cli",
        },
        "Body text.",
    )

    text = path.read_text(encoding="utf-8")

    assert "author:" not in text
    assert "pr:" not in text
    assert "component:" not in text
    assert "authors:" in text
    assert "prs:" in text
    assert "components:" in text


def test_read_entry_preserves_plural_components(tmp_path: Path) -> None:
    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\ncomponents:\n  - cli\n  - api\n---\nBody text.\n",
        encoding="utf-8",
    )

    entry = read_entry(entry_file)

    assert entry.metadata["components"] == ["cli", "api"]
    assert entry.components == ["cli", "api"]
