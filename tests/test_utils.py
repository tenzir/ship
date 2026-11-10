"""Unit tests for shared utilities."""

from __future__ import annotations

from tenzir_ship.utils import extract_excerpt, slugify


def test_extract_excerpt_collapses_first_paragraph() -> None:
    text = """First sentence that spans
multiple lines thanks to wrapping.

Additional details in the second paragraph."""
    assert extract_excerpt(text) == "First sentence that spans multiple lines thanks to wrapping."


def test_extract_excerpt_handles_whitespace_only() -> None:
    assert extract_excerpt("   \n  ") == ""


def test_slugify_preserves_non_ascii_project_names() -> None:
    assert slugify("東京") == "東京"
