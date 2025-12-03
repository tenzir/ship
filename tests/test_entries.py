"""Tests for entry helper utilities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tenzir_changelog.entries import iter_entries, read_entry, sort_entries_desc, write_entry


def test_sort_entries_desc_orders_by_created_datetime(tmp_path: Path) -> None:
    """Entries are sorted from newest to oldest by created datetime."""
    metadata_a = {
        "title": "Entry A",
        "type": "change",
        "component": "cli",
        "created": datetime(2024, 1, 1, 10, 0, 0),
    }
    metadata_b = {
        "title": "Entry B",
        "type": "change",
        "component": "cli",
        "created": datetime(2024, 2, 1, 11, 0, 0),
    }

    write_entry(tmp_path, dict(metadata_a), "First body")
    write_entry(tmp_path, dict(metadata_b), "Second body")

    entries = list(iter_entries(tmp_path))
    ordered = sort_entries_desc(entries)

    # Entry B is newer, so it should come first in descending order
    assert [entry.entry_id for entry in ordered] == ["entry-b", "entry-a"]
    assert ordered[0].created_at == datetime(2024, 2, 1, 11, 0, 0)
    assert ordered[1].created_at == datetime(2024, 1, 1, 10, 0, 0)


def test_read_entry_normalizes_singular_pr_to_prs(tmp_path: Path) -> None:
    """Singular `pr` key should be normalized to plural `prs` list."""
    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\npr: 42\n---\nBody text.\n",
        encoding="utf-8",
    )

    entry = read_entry(entry_file)
    assert "pr" not in entry.metadata
    assert entry.metadata["prs"] == [42]


def test_read_entry_normalizes_singular_author_to_authors(tmp_path: Path) -> None:
    """Singular `author` key should be normalized to plural `authors` list."""
    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\nauthor: codex\n---\nBody text.\n",
        encoding="utf-8",
    )

    entry = read_entry(entry_file)
    assert "author" not in entry.metadata
    assert entry.metadata["authors"] == ["codex"]


def test_read_entry_rejects_both_pr_and_prs(tmp_path: Path) -> None:
    """Having both `pr` and `prs` should raise an error."""
    import pytest

    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\npr: 99\nprs:\n  - 42\n  - 43\n---\nBody.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot have both 'pr' and 'prs'"):
        read_entry(entry_file)


def test_read_entry_rejects_both_author_and_authors(tmp_path: Path) -> None:
    """Having both `author` and `authors` should raise an error."""
    import pytest

    entry_file = tmp_path / "test.md"
    entry_file.write_text(
        "---\ntitle: Test Entry\ntype: feature\nauthor: ignored\nauthors:\n  - alice\n  - bob\n---\nBody.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot have both 'author' and 'authors'"):
        read_entry(entry_file)
