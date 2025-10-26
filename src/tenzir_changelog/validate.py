"""Validation routines for changelog data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import Config
from .entries import ENTRY_TYPES, Entry, iter_entries
from .releases import (
    ReleaseManifest,
    iter_release_manifests,
    load_release_entry,
    resolve_release_entry_path,
)


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
    component = entry.component
    if component and config.components and component not in config.components:
        allowed = ", ".join(config.components)
        yield ValidationIssue(
            entry.path,
            f"Unknown component '{component}'. Allowed components: {allowed}",
        )


def validate_release_ids(
    entries: Iterable[Entry],
    releases: Iterable[ReleaseManifest],
    project_root: Path,
    issues: list[ValidationIssue],
) -> None:
    """Ensure release manifests reference existing entry IDs."""
    entry_ids = {entry.entry_id for entry in entries}
    for manifest in releases:
        for entry_id in manifest.entries:
            if entry_id in entry_ids:
                continue
            entry_path = resolve_release_entry_path(project_root, manifest, entry_id)
            if entry_path is None:
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
        for entry_id in manifest.entries:
            try:
                entry = load_release_entry(project_root, manifest, entry_id)
            except ValueError as exc:
                entry_path = resolve_release_entry_path(project_root, manifest, entry_id)
                issues.append(ValidationIssue(entry_path or manifest.path or Path(""), str(exc)))
                continue
            if entry is None:
                continue
            release_entries.append(entry)

    all_entries = entries + release_entries
    for entry in all_entries:
        issues.extend(validate_entry(entry, config))

    validate_release_ids(all_entries, releases, project_root, issues)
    return issues
