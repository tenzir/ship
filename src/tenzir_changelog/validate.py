"""Validation routines for changelog data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import Config
from .entries import ENTRY_TYPES, Entry, iter_entries, read_entry
from .releases import ReleaseManifest, iter_release_manifests


@dataclass
class ValidationIssue:
    """Represents a warning or error encountered during validation."""

    path: Path
    message: str
    severity: str = "error"  # can be "error" or "warning"


def validate_entry(entry: Entry, config: Config) -> Iterable[ValidationIssue]:
    """Validate a single entry."""
    metadata = entry.metadata
    title = metadata.get("title")
    if not title:
        yield ValidationIssue(entry.path, "Missing title")
    entry_type = metadata.get("type")
    if entry_type not in ENTRY_TYPES:
        yield ValidationIssue(
            entry.path,
            f"Unknown type '{entry_type}'. Allowed types: {', '.join(ENTRY_TYPES)}",
        )
    project = entry.project or config.id
    if project != config.id:
        yield ValidationIssue(
            entry.path,
            f"Unknown project '{project}'. Expected '{config.id}'.",
        )


def validate_release_ids(
    entries: Iterable[Entry],
    releases: Iterable[ReleaseManifest],
    issues: list[ValidationIssue],
) -> None:
    """Ensure release manifests reference existing entry IDs."""
    entry_ids = {entry.entry_id for entry in entries}
    for manifest in releases:
        release_dir = manifest.path.parent if manifest.path else None
        for entry_id in manifest.entries:
            if entry_id in entry_ids:
                continue
            file_exists = False
            if release_dir is not None:
                entries_dir = release_dir / "entries"
                archive_paths = [
                    entries_dir / f"{entry_id}.md",
                    release_dir / f"{entry_id}.md",
                ]
                file_exists = any(path.exists() for path in archive_paths)
            if not file_exists:
                issues.append(
                    ValidationIssue(
                        manifest.path or Path(""),
                        f"Release references missing entry id '{entry_id}'",
                    )
                )


def run_validation(project_root: Path, config: Config) -> list[ValidationIssue]:
    """Validate entries and releases, returning a list of issues."""
    issues: list[ValidationIssue] = []
    releases = list(iter_release_manifests(project_root))
    entries = list(iter_entries(project_root))
    release_entries: list[Entry] = []
    for manifest in releases:
        release_dir = manifest.path.parent if manifest.path else None
        if release_dir is None:
            continue
        for entry_id in manifest.entries:
            entry_path = release_dir / "entries" / f"{entry_id}.md"
            if not entry_path.exists():
                entry_path = release_dir / f"{entry_id}.md"
            if not entry_path.exists():
                continue
            try:
                release_entries.append(read_entry(entry_path))
            except ValueError as exc:
                issues.append(ValidationIssue(entry_path, str(exc)))

    all_entries = entries + release_entries
    for entry in all_entries:
        issues.extend(validate_entry(entry, config))

    for manifest in releases:
        if manifest.project and manifest.project != config.id:
            issues.append(
                ValidationIssue(
                    manifest.path or Path(""),
                    f"Release project '{manifest.project}' does not match configured project '{config.id}'.",
                )
            )
    validate_release_ids(all_entries, releases, issues)
    return issues
