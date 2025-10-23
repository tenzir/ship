"""Release manifest management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import yaml
from yaml.nodes import Node

from .entries import Entry, read_entry


def _represent_date(dumper: yaml.SafeDumper, data: date) -> Node:
    return dumper.represent_scalar("tag:yaml.org,2002:timestamp", data.isoformat())


yaml.SafeDumper.add_representer(date, _represent_date)

NOTES_FILENAME = "notes.md"


def _extract_release_summary(notes_path: Path) -> str:
    if not notes_path.exists():
        return ""
    summary_lines: list[str] = []
    collecting = False
    for line in notes_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            if collecting:
                break
            continue
        if stripped.startswith("#"):
            if collecting:
                break
            continue
        summary_lines.append(stripped)
        collecting = True
    return " ".join(summary_lines).strip()


RELEASE_DIR = Path("releases")


@dataclass
class ReleaseManifest:
    """Representation of a release manifest."""

    version: str
    created: date
    entries: list[str] = field(default_factory=list)
    title: str = ""
    description: str = ""
    intro: str | None = None
    path: Path | None = None


def release_directory(project_root: Path) -> Path:
    """Return the path containing release manifests."""
    return project_root / RELEASE_DIR


def _parse_created_date(raw_value: object | None) -> date:
    if raw_value is None:
        return date.today()
    return date.fromisoformat(str(raw_value))


def iter_release_manifests(project_root: Path) -> Iterable[ReleaseManifest]:
    """Yield release manifests from disk."""
    directory = release_directory(project_root)
    if not directory.exists():
        return

    manifest_paths = sorted(directory.glob("*/manifest.yaml"))

    for path in manifest_paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        raw_description = str(data.get("description", "") or "").strip()
        raw_intro = str(data.get("intro", "") or "").strip()
        created_value = _parse_created_date(data.get("created"))

        version_value = data.get("version") or path.parent.name

        title_value = str(data.get("title", ""))
        if not title_value:
            title_value = str(version_value)

        manifest = ReleaseManifest(
            version=str(version_value),
            created=created_value,
            title=title_value,
            description=raw_description,
            intro=raw_intro or None,
            path=path,
        )
        entries_dir = path.parent / "entries"
        entry_files = sorted(entries_dir.glob("*.md"))
        manifest.entries = [entry_file.stem for entry_file in entry_files]
        if not manifest.description:
            summary = _extract_release_summary(
                _manifest_root(project_root, manifest) / NOTES_FILENAME
            )
            if summary:
                manifest.description = summary
        yield manifest


def used_entry_ids(project_root: Path) -> set[str]:
    """Return a set containing entry IDs that already belong to a release."""
    used = set()
    for manifest in iter_release_manifests(project_root):
        used.update(manifest.entries)
    return used


def unused_entries(entries: Iterable[Entry], used_ids: set[str]) -> list[Entry]:
    """Filter entries that have not yet been included in a release."""
    return [entry for entry in entries if entry.entry_id not in used_ids]


def write_release_manifest(
    project_root: Path,
    manifest: ReleaseManifest,
    readme_content: str,
) -> Path:
    """Serialize and store a release manifest alongside release notes."""
    directory = release_directory(project_root)
    directory.mkdir(parents=True, exist_ok=True)
    release_dir = directory / manifest.version
    if release_dir.exists():
        raise FileExistsError(f"Release directory {release_dir} already exists")
    release_dir.mkdir(parents=True, exist_ok=False)

    manifest_path = release_dir / "manifest.yaml"
    if manifest_path.exists():
        raise FileExistsError(f"Release manifest {manifest_path} already exists")
    payload: dict[str, object] = {
        "created": manifest.created,
    }
    if manifest.intro:
        payload["intro"] = manifest.intro
    manifest_payload = yaml.safe_dump(payload, sort_keys=False)
    manifest_path.write_text(manifest_payload, encoding="utf-8")

    notes_path = release_dir / NOTES_FILENAME
    normalized_notes = readme_content.strip()
    if normalized_notes:
        notes_path.write_text(normalized_notes + "\n", encoding="utf-8")
    else:
        notes_path.write_text("", encoding="utf-8")

    manifest.path = manifest_path
    return manifest_path


def _manifest_root(project_root: Path, manifest: ReleaseManifest) -> Path:
    """Return the base directory for a release manifest."""
    if manifest.path is None:
        return release_directory(project_root) / manifest.version
    path = manifest.path
    if path.is_dir():
        return path
    if path.name.lower() == "manifest.yaml":
        return path.parent
    return path.parent


def resolve_release_entry_path(
    project_root: Path, manifest: ReleaseManifest, entry_id: str
) -> Path | None:
    """Return the path to an entry file belonging to a release, if present."""
    root = _manifest_root(project_root, manifest)
    entry_path = root / "entries" / f"{entry_id}.md"
    if entry_path.exists():
        return entry_path
    return None


def load_release_entry(
    project_root: Path, manifest: ReleaseManifest, entry_id: str
) -> Entry | None:
    """Load a release entry as an Entry instance."""
    entry_path = resolve_release_entry_path(project_root, manifest, entry_id)
    if entry_path is None:
        return None
    return read_entry(entry_path)


def collect_release_entries(project_root: Path) -> dict[str, Entry]:
    """Return a mapping of entry ids to entries across all releases."""
    collected: dict[str, Entry] = {}
    for manifest in iter_release_manifests(project_root):
        for entry_id in manifest.entries:
            if entry_id in collected:
                continue
            entry = load_release_entry(project_root, manifest, entry_id)
            if entry is not None:
                collected[entry_id] = entry
    return collected


def build_entry_release_index(
    project_root: Path, *, project: Optional[str] = None
) -> dict[str, list[str]]:
    """Return a mapping from entry id to associated release versions."""
    index: dict[str, list[str]] = {}
    for manifest in iter_release_manifests(project_root):
        for entry_id in manifest.entries:
            versions = index.setdefault(entry_id, [])
            if manifest.version not in versions:
                versions.append(manifest.version)
    for versions in index.values():
        versions.sort()
    return index
