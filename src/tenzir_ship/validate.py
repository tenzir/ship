"""Validation routines for changelog data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from .config import Config
from .entries import ENTRY_TYPES, Entry, iter_entries
from .releases import (
    ReleaseManifest,
    iter_release_manifests,
    load_release_entry,
    resolve_release_entry_path,
)

if TYPE_CHECKING:
    from .modules import Module


_ALLOWED_CHANGELOG_ROOT_ITEMS = {"config.yaml", "unreleased", "releases"}
_ALLOWED_RELEASE_ITEMS = {"manifest.yaml", "notes.md", "entries"}


@dataclass
class ValidationIssue:
    """Represents a warning or error encountered during validation."""

    path: Path
    message: str
    severity: str = "error"  # can be "error" or "warning"


def _iter_non_hidden_children(directory: Path) -> Iterable[Path]:
    """Yield non-hidden direct children of a directory in deterministic order."""
    if not directory.exists() or not directory.is_dir():
        return
    for child in sorted(directory.iterdir(), key=lambda path: path.name):
        if child.name.startswith("."):
            continue
        yield child


def _validate_changelog_structure(project_root: Path) -> list[ValidationIssue]:
    """Validate on-disk changelog directory layout for a project root."""
    issues: list[ValidationIssue] = []

    # Check root-level allowed items.
    for child in _iter_non_hidden_children(project_root):
        if child.name in _ALLOWED_CHANGELOG_ROOT_ITEMS:
            continue
        issues.append(
            ValidationIssue(
                child,
                (
                    f"Unexpected item in changelog root: '{child.name}'. "
                    "Allowed: config.yaml, unreleased, releases."
                ),
            )
        )

    config_path = project_root / "config.yaml"
    if config_path.exists() and not config_path.is_file():
        issues.append(ValidationIssue(config_path, "'config.yaml' must be a file."))

    unreleased_dir = project_root / "unreleased"
    if unreleased_dir.exists():
        if not unreleased_dir.is_dir():
            issues.append(ValidationIssue(unreleased_dir, "'unreleased' must be a directory."))
        else:
            for child in _iter_non_hidden_children(unreleased_dir):
                if child.is_file() and child.suffix == ".md":
                    continue
                issues.append(
                    ValidationIssue(
                        child,
                        (
                            f"Unexpected item in 'unreleased/': '{child.name}'. "
                            "Only Markdown (*.md) files are allowed."
                        ),
                    )
                )

    releases_dir = project_root / "releases"
    if releases_dir.exists():
        if not releases_dir.is_dir():
            issues.append(ValidationIssue(releases_dir, "'releases' must be a directory."))
            return issues

        for release_dir in _iter_non_hidden_children(releases_dir):
            if not release_dir.is_dir():
                issues.append(
                    ValidationIssue(
                        release_dir,
                        (
                            f"Unexpected item in 'releases/': '{release_dir.name}'. "
                            "Release directories only."
                        ),
                    )
                )
                continue

            manifest_path = release_dir / "manifest.yaml"
            if not manifest_path.exists():
                issues.append(
                    ValidationIssue(
                        manifest_path,
                        f"Release '{release_dir.name}' is missing required file 'manifest.yaml'.",
                    )
                )
            elif not manifest_path.is_file():
                issues.append(
                    ValidationIssue(
                        manifest_path,
                        f"Release '{release_dir.name}' has non-file 'manifest.yaml'.",
                    )
                )

            for child in _iter_non_hidden_children(release_dir):
                if child.name in _ALLOWED_RELEASE_ITEMS:
                    continue
                issues.append(
                    ValidationIssue(
                        child,
                        (
                            f"Unexpected item in release '{release_dir.name}/': '{child.name}'. "
                            "Allowed: manifest.yaml, notes.md, entries."
                        ),
                    )
                )

            notes_path = release_dir / "notes.md"
            if notes_path.exists() and not notes_path.is_file():
                issues.append(
                    ValidationIssue(
                        notes_path,
                        f"Release '{release_dir.name}' has non-file 'notes.md'.",
                    )
                )

            entries_dir = release_dir / "entries"
            if entries_dir.exists():
                if not entries_dir.is_dir():
                    issues.append(
                        ValidationIssue(
                            entries_dir,
                            f"Release '{release_dir.name}' has non-directory 'entries'.",
                        )
                    )
                else:
                    for child in _iter_non_hidden_children(entries_dir):
                        if child.is_file() and child.suffix == ".md":
                            continue
                        issues.append(
                            ValidationIssue(
                                child,
                                (
                                    "Unexpected item in release "
                                    f"'{release_dir.name}/entries/': '{child.name}'. "
                                    "Only Markdown (*.md) files are allowed."
                                ),
                            )
                        )

    return issues


def run_structure_validation(project_root: Path) -> list[ValidationIssue]:
    """Validate changelog structure for a project root."""
    return _validate_changelog_structure(project_root)


def run_structure_validation_with_modules(
    project_root: Path,
    modules: list["Module"],
) -> list[ValidationIssue]:
    """Validate changelog structure for parent project and discovered modules."""
    issues = run_structure_validation(project_root)
    for module in modules:
        for issue in run_structure_validation(module.root):
            issues.append(
                ValidationIssue(
                    path=issue.path,
                    message=f"[{module.config.id}] {issue.message}",
                    severity=issue.severity,
                )
            )
    return issues


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
    entry_components = entry.components
    if entry_components and config.components:
        unknown = [c for c in entry_components if c not in config.components]
        if unknown:
            allowed = ", ".join(config.components)
            unknown_display = ", ".join(f"'{c}'" for c in unknown)
            yield ValidationIssue(
                entry.path,
                f"Unknown component(s) {unknown_display}. Allowed components: {allowed}",
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
    issues: list[ValidationIssue] = run_structure_validation(project_root)
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


def validate_modules(
    parent_root: Path,
    config: Config,
    modules: list["Module"],
) -> list[ValidationIssue]:
    """Validate module configuration.

    Checks:
    - Module ID uniqueness (no duplicates among modules or with parent)
    - No circular references (module cannot reference parent)
    """
    issues: list[ValidationIssue] = []

    # Check for duplicate module IDs
    seen_ids: dict[str, Path] = {config.id: parent_root}
    for module in modules:
        module_id = module.config.id
        if module_id in seen_ids:
            other_path = seen_ids[module_id]
            issues.append(
                ValidationIssue(
                    module.root,
                    f"Duplicate module ID '{module_id}' (also at {other_path})",
                )
            )
        else:
            seen_ids[module_id] = module.root

        # Check that module doesn't reference parent (circular reference)
        if module.root.resolve() == parent_root.resolve():
            issues.append(
                ValidationIssue(
                    parent_root,
                    "Module pattern matches parent directory (circular reference)",
                )
            )

    return issues


def run_validation_with_modules(
    project_root: Path,
    config: Config,
    modules: list["Module"],
) -> list[ValidationIssue]:
    """Validate parent and all modules, returning combined issues.

    Issues from modules are prefixed with the module ID for clarity.
    """
    issues: list[ValidationIssue] = []

    # Validate module configuration itself
    issues.extend(validate_modules(project_root, config, modules))

    # Validate parent project
    parent_issues = run_validation(project_root, config)
    issues.extend(parent_issues)

    # Validate each module
    for module in modules:
        module_issues = run_validation(module.root, module.config)
        # Prefix issues with module ID for clarity
        for issue in module_issues:
            prefixed_issue = ValidationIssue(
                path=issue.path,
                message=f"[{module.config.id}] {issue.message}",
                severity=issue.severity,
            )
            issues.append(prefixed_issue)

    return issues
