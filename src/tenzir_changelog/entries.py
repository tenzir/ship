"""Entry management utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml
from click import ClickException

from .utils import coerce_datetime, slugify

UNRELEASED_DIR = Path("unreleased")
ENTRY_TYPES = ("breaking", "feature", "bugfix", "change")


@dataclass
class Entry:
    """Representation of a changelog entry file."""

    entry_id: str
    metadata: dict[str, Any]
    body: str
    path: Path

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", "Untitled"))

    @property
    def type(self) -> str:
        return str(self.metadata.get("type", "change"))

    @property
    def components(self) -> list[str]:
        """Return the list of components for the entry."""
        value = self.metadata.get("components")
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    @property
    def component(self) -> Optional[str]:
        """Return the first component (for backwards compatibility)."""
        components = self.components
        return components[0] if components else None

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
    def created_at(self) -> Optional[datetime]:
        return coerce_datetime(self.metadata.get("created"))

    @property
    def created_date(self) -> Optional[date]:
        """Return just the date portion of created_at for display."""
        dt = self.created_at
        return dt.date() if dt else None


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
    _normalize_prs_metadata(metadata)
    _normalize_authors_metadata(metadata)
    _normalize_components_metadata(metadata)
    entry_id = path.stem
    return Entry(
        entry_id=entry_id,
        metadata=metadata,
        body=body.strip(),
        path=path,
    )


def iter_entries(project_root: Path) -> Iterable[Entry]:
    """Yield changelog entries from disk."""
    directory = entry_directory(project_root)
    if not directory.exists():
        return
    for path in sorted(directory.glob("*.md")):
        try:
            yield read_entry(path)
        except yaml.YAMLError as exc:
            raise ClickException(
                f"Failed to parse YAML frontmatter in '{path.name}': {exc}\n\n"
                "Hint: If your title or other fields contain colons, "
                "wrap them in quotes."
            ) from exc
        except ValueError as exc:
            raise ClickException(f"Failed to read entry '{path.name}': {exc}") from exc


def _entry_sort_key(entry: Entry) -> tuple[datetime, str]:
    """Return a tuple for deterministic entry ordering.

    Orders by created datetime (ascending) with entry_id as tie-breaker.
    Entries without a created datetime sort to the beginning (epoch).
    """
    created = entry.created_at or datetime.min.replace(tzinfo=timezone.utc)
    return created, entry.entry_id


def sort_entries_desc(entries: Iterable[Entry]) -> list[Entry]:
    """Return entries sorted from newest to oldest by created datetime."""
    return sorted(entries, key=_entry_sort_key, reverse=True)


def generate_entry_id(title: str) -> str:
    """Generate an entry id from the title slug."""
    slug = slugify(title)
    if not slug:
        raise ValueError("Cannot generate entry ID: title produces an empty slug.")
    return slug[:80]


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


def _normalize_created_metadata(
    metadata: dict[str, Any],
    *,
    default_now: bool = False,
) -> None:
    """Ensure the created field is stored as a datetime object."""
    if "created" not in metadata or metadata["created"] is None:
        metadata.pop("created", None)
        if default_now:
            metadata["created"] = datetime.now(timezone.utc)
        return
    raw_created = metadata["created"]
    created_value = coerce_datetime(raw_created)
    if created_value is not None:
        metadata["created"] = created_value
        return
    if isinstance(raw_created, str) and not raw_created.strip():
        metadata.pop("created", None)
        if default_now:
            metadata["created"] = datetime.now(timezone.utc)
        return
    raise ValueError(f"Invalid created datetime value: {raw_created!r}")


def _normalize_prs_metadata(metadata: dict[str, Any]) -> None:
    """Normalize singular `pr` key to plural `prs` key."""
    if "pr" in metadata:
        if "prs" in metadata:
            raise ValueError("Entry cannot have both 'pr' and 'prs' keys; use one or the other.")
        pr_value = metadata.pop("pr")
        if pr_value is not None:
            metadata["prs"] = [pr_value] if not isinstance(pr_value, list) else pr_value


def _normalize_authors_metadata(metadata: dict[str, Any]) -> None:
    """Normalize singular `author` key to plural `authors` key."""
    if "author" in metadata:
        if "authors" in metadata:
            raise ValueError(
                "Entry cannot have both 'author' and 'authors' keys; use one or the other."
            )
        author_value = metadata.pop("author")
        if author_value is not None:
            metadata["authors"] = (
                [author_value] if not isinstance(author_value, list) else author_value
            )


def _normalize_components_metadata(metadata: dict[str, Any]) -> None:
    """Normalize singular `component` key to plural `components` key."""
    if "component" in metadata:
        if "components" in metadata:
            raise ValueError(
                "Entry cannot have both 'component' and 'components' keys; use one or the other."
            )
        component_value = metadata.pop("component")
        if component_value is not None:
            if isinstance(component_value, str):
                stripped = component_value.strip()
                if stripped:
                    metadata["components"] = [stripped]
            elif isinstance(component_value, list):
                normalized = [str(item).strip() for item in component_value if str(item).strip()]
                if normalized:
                    metadata["components"] = normalized
    elif "components" in metadata:
        # Normalize existing plural key
        components_value = metadata["components"]
        if components_value is not None:
            if isinstance(components_value, str):
                stripped = components_value.strip()
                metadata["components"] = [stripped] if stripped else None
            elif isinstance(components_value, list):
                normalized = [str(item).strip() for item in components_value if str(item).strip()]
                metadata["components"] = normalized if normalized else None
            if metadata.get("components") is None:
                metadata.pop("components", None)


class _IndentedDumper(yaml.SafeDumper):
    """Custom YAML dumper that indents list items under their parent key."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        """Override to always indent sequences."""
        return super().increase_indent(flow=flow, indentless=False)


def format_frontmatter(metadata: dict[str, Any]) -> str:
    """Render metadata as YAML frontmatter for an entry file."""
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        cleaned[key] = value
    yaml_block = yaml.dump(
        cleaned,
        Dumper=_IndentedDumper,
        sort_keys=False,
        default_flow_style=False,
        indent=2,
    ).strip()
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
    _normalize_components_metadata(metadata)

    if entry_id is None:
        title = metadata.get("title")
        if not title:
            raise ValueError("Cannot create entry: 'title' is required in metadata.")
        entry_id = generate_entry_id(title)

    path = directory / f"{entry_id}.md"
    if path.exists():
        raise ValueError(
            f"An entry with id '{entry_id}' already exists. "
            "Please use a different title to generate a unique entry id."
        )

    _normalize_created_metadata(metadata, default_now=True)
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
    from .releases import collect_release_entries

    for project_root, config in projects:
        project_id = getattr(config, "id", slugify(project_root.name))
        project_name = getattr(config, "name", str(project_root.name))
        # Collect all entries (unreleased and released), avoiding duplicates
        entry_map: dict[str, Entry] = {}
        for entry in iter_entries(project_root):
            entry_map[entry.entry_id] = entry
        for entry_id, entry in collect_release_entries(project_root).items():
            if entry_id not in entry_map:
                entry_map[entry_id] = entry
        for entry in entry_map.values():
            yield MultiProjectEntry(
                entry=entry,
                project_root=project_root,
                project_id=project_id,
                project_name=project_name,
            )
