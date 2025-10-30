"""Entry management utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml
from click import ClickException

from .utils import coerce_date, slugify

UNRELEASED_DIR = Path("unreleased")
ENTRY_TYPES = ("breaking", "feature", "bugfix", "change")
ENTRY_PREFIX_WIDTH = 2
ENTRY_FILENAME_SEPARATOR = "-"


@dataclass
class Entry:
    """Representation of a changelog entry file."""

    entry_id: str
    metadata: dict[str, Any]
    body: str
    path: Path
    sequence: int

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", "Untitled"))

    @property
    def type(self) -> str:
        return str(self.metadata.get("type", "change"))

    @property
    def component(self) -> Optional[str]:
        value = self.metadata.get("component")
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        return str(value).strip() or None

    @property
    def project(self) -> Optional[str]:
        """Return the single project an entry belongs to."""
        try:
            return normalize_project(self.metadata)
        except ValueError as exc:
            raise ValueError(
                f"Entry '{self.entry_id}' has invalid project metadata: {exc}"
            ) from exc

    @property
    def projects(self) -> list[str]:
        project = self.project
        return [project] if project else []

    @property
    def products(self) -> list[str]:  # backwards compatibility
        return self.projects

    @property
    def created_at(self) -> Optional[date]:
        return coerce_date(self.metadata.get("created"))


def entry_directory(project_root: Path) -> Path:
    """Return the directory containing unreleased changelog entries."""
    return project_root / UNRELEASED_DIR


def read_entry(path: Path) -> Entry:
    """Parse a markdown entry file with YAML frontmatter."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        raise ValueError(f"Entry {path} missing YAML frontmatter")

    _, _, remainder = content.partition("---\n")
    frontmatter, _, body = remainder.partition("\n---\n")
    metadata = yaml.safe_load(frontmatter) or {}
    _normalize_created_metadata(metadata)
    _normalize_component_metadata(metadata, required=False)
    entry_id = path.stem
    sequence = _parse_entry_sequence(entry_id)
    return Entry(
        entry_id=entry_id,
        metadata=metadata,
        body=body.strip(),
        path=path,
        sequence=sequence,
    )


def _parse_entry_sequence(entry_id: str) -> int:
    """Extract the numeric prefix from an entry identifier."""
    if ENTRY_FILENAME_SEPARATOR in entry_id:
        prefix, _ = entry_id.split(ENTRY_FILENAME_SEPARATOR, 1)
    else:
        prefix = entry_id
    if not prefix.isdigit():
        raise ValueError(f"Entry id '{entry_id}' must start with a numeric prefix.")
    if len(prefix) < ENTRY_PREFIX_WIDTH:
        raise ValueError(f"Entry id '{entry_id}' must use at least {ENTRY_PREFIX_WIDTH} digits.")
    return int(prefix)


def _next_entry_sequence(directory: Path) -> int:
    """Return the next sequence number for the given entry directory."""
    max_sequence = 0
    for path in directory.glob("*.md"):
        existing_sequence = _parse_entry_sequence(path.stem)
        max_sequence = max(max_sequence, existing_sequence)
    return max_sequence + 1 if max_sequence else 1


def iter_entries(project_root: Path) -> Iterable[Entry]:
    """Yield changelog entries from disk."""
    directory = entry_directory(project_root)
    if not directory.exists():
        return
    for path in sorted(directory.glob("*.md")):
        try:
            yield read_entry(path)
        except ValueError as exc:
            raise ClickException(f"Failed to read entry '{path.name}': {exc}") from exc


def _entry_sort_key(entry: Entry) -> tuple[int, str]:
    """Return a tuple for deterministic entry ordering."""
    return entry.sequence, entry.entry_id


def sort_entries_desc(entries: Iterable[Entry]) -> list[Entry]:
    """Return entries sorted from highest to lowest numeric prefix."""
    return sorted(entries, key=_entry_sort_key, reverse=True)


def generate_entry_id(sequence: int, seed: Optional[str] = None) -> str:
    """Generate a numeric-prefixed entry id based on optional seed."""
    if sequence < 10**ENTRY_PREFIX_WIDTH:
        prefix = f"{sequence:0{ENTRY_PREFIX_WIDTH}d}"
    else:
        prefix = str(sequence)
    if seed:
        slug = slugify(seed)
        if slug:
            return f"{prefix}{ENTRY_FILENAME_SEPARATOR}{slug[:80]}"
    return prefix


def _coerce_project(value: Any, *, source: str) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (list, tuple, set)):
        normalized = [str(item).strip() for item in value if str(item).strip()]
        if not normalized:
            return None
        if len(normalized) > 1:
            raise ValueError(
                f"{source} must contain a single project, got: {', '.join(normalized)}"
            )
        return normalized[0]
    return str(value).strip() or None


def normalize_project(
    metadata: dict[str, Any],
    default: Optional[str] = None,
) -> Optional[str]:
    """Normalize project metadata to the singular `project` key."""
    project = _coerce_project(metadata.get("project"), source="project")
    legacy_keys = ("projects", "products")

    if project is None:
        for key in legacy_keys:
            if key in metadata:
                project = _coerce_project(metadata.get(key), source=key)
            metadata.pop(key, None)
            if project is not None:
                break
        if project is None and default is not None:
            project = default
    else:
        for key in legacy_keys:
            metadata.pop(key, None)

    if project is None:
        metadata.pop("project", None)
        return None

    metadata["project"] = project
    return project


def _normalize_component_metadata(
    metadata: dict[str, Any],
    *,
    required: bool,
) -> Optional[str]:
    """Ensure component metadata is stored as a trimmed string."""
    value = metadata.get("component")
    if value is None:
        if required:
            raise ValueError("Entry metadata missing required 'component' field.")
        metadata.pop("component", None)
        return None
    component = str(value).strip()
    if not component:
        if required:
            raise ValueError("Entry metadata 'component' must be a non-empty string.")
        metadata.pop("component", None)
        return None
    metadata["component"] = component
    return component


def _normalize_created_metadata(
    metadata: dict[str, Any],
    *,
    default_today: bool = False,
) -> None:
    """Ensure the created field is stored as a date object."""
    if "created" not in metadata or metadata["created"] is None:
        metadata.pop("created", None)
        if default_today:
            metadata["created"] = date.today()
        return
    raw_created = metadata["created"]
    created_value = coerce_date(raw_created)
    if created_value is not None:
        metadata["created"] = created_value
        return
    if isinstance(raw_created, str) and not raw_created.strip():
        metadata.pop("created", None)
        if default_today:
            metadata["created"] = date.today()
        return
    raise ValueError(f"Invalid created date value: {raw_created!r}")


def format_frontmatter(metadata: dict[str, Any]) -> str:
    """Render metadata as YAML frontmatter for an entry file."""
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        cleaned[key] = value
    yaml_block = yaml.safe_dump(cleaned, sort_keys=False).strip()
    return f"---\n{yaml_block}\n---\n"


def write_entry(
    project_root: Path,
    metadata: dict[str, Any],
    body: str,
    entry_id: Optional[str] = None,
    *,
    default_project: Optional[str] = None,
) -> Path:
    """Write a new entry file and return its path."""
    directory = entry_directory(project_root)
    directory.mkdir(parents=True, exist_ok=True)
    entry_type = str(metadata.get("type", "change"))
    if entry_type not in ENTRY_TYPES:
        raise ValueError(
            f"Unknown entry type '{entry_type}'. Expected one of: {', '.join(ENTRY_TYPES)}"
        )
    metadata["type"] = entry_type
    project_value = normalize_project(metadata, default=default_project)
    if default_project is not None and project_value == default_project:
        metadata.pop("project", None)
    _normalize_component_metadata(metadata, required=False)
    if entry_id is None:
        sequence = _next_entry_sequence(directory)
        entry_id = generate_entry_id(sequence, metadata.get("title"))
        path = directory / f"{entry_id}.md"
        while path.exists():
            sequence += 1
            entry_id = generate_entry_id(sequence, metadata.get("title"))
            path = directory / f"{entry_id}.md"
    else:
        _parse_entry_sequence(entry_id)
        path = directory / f"{entry_id}.md"
        if path.exists():
            base = entry_id
            counter = 1
            while True:
                candidate = f"{base}-{counter}"
                candidate_path = directory / f"{candidate}.md"
                if not candidate_path.exists():
                    entry_id = candidate
                    path = candidate_path
                    break
                counter += 1

    _normalize_created_metadata(metadata, default_today=True)
    frontmatter = format_frontmatter(metadata)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(frontmatter)
        if body:
            handle.write("\n" + body.strip() + "\n")
    return path


@dataclass
class MultiProjectEntry:
    """An entry with its associated project information."""

    entry: Entry
    project_root: Path
    project_id: str
    project_name: str


def iter_multi_project_entries(projects: list[tuple[Path, Any]]) -> Iterable[MultiProjectEntry]:
    """Yield entries from multiple projects with project context.

    Args:
        projects: List of (project_root, config) tuples

    Yields:
        MultiProjectEntry instances with entry and project information
    """
    for project_root, config in projects:
        project_id = getattr(config, "id", slugify(project_root.name))
        project_name = getattr(config, "name", str(project_root.name))
        for entry in iter_entries(project_root):
            yield MultiProjectEntry(
                entry=entry,
                project_root=project_root,
                project_id=project_id,
                project_name=project_name,
            )
